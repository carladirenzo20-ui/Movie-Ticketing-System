"""Run with: python -m unittest discover -s tests -v

Uses a real MySQL server. Each test creates and removes its own database;
cinema_db is never changed. Requires permission to create databases/triggers.
"""

import os
from pathlib import Path
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from decimal import Decimal
from io import StringIO
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from admin import Admin, add_mov_screen_query, admin_menu
from booking import BookingError, book_tickets
from client import Client, client_menu
from database import login


class MySQLTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", "root"),
            "connection_timeout": 5,
        }
        self.db = mysql.connector.connect(**self.config)
        self.addCleanup(self.db.close)
        self.database = "cinema_test_" + uuid4().hex
        cursor = self.db.cursor()
        cursor.execute(f"CREATE DATABASE `{self.database}`")
        self.addCleanup(self.drop_database)
        cursor.execute(f"USE `{self.database}`")
        self.config["database"] = self.database

        # Use the same schema and seed files supplied for the application.
        for filename in ("schema.sql", "data.sql"):
            source = (ROOT / filename).read_text(encoding="utf-8")
            source = "\n".join(line for line in source.splitlines()
                               if not line.lstrip().startswith("--"))
            for statement in source.split(";"):
                statement = statement.strip()
                if statement and not statement.upper().startswith(
                        ("DROP DATABASE", "CREATE DATABASE", "USE ")):
                    cursor.execute(statement)
        self.db.commit()
        cursor.close()

    def drop_database(self):
        self.db.rollback()
        cursor = self.db.cursor()
        cursor.execute(f"DROP DATABASE `{self.database}`")
        cursor.close()

    def query(self, sql, params=()):
        cursor = self.db.cursor(buffered=True)
        try:
            cursor.execute(sql, params)
            result = cursor.fetchall() if cursor.with_rows else cursor.rowcount
            self.db.commit()
            return result
        finally:
            cursor.close()


class Parts67Tests(MySQLTests):
    def purchase(self, quantity=1, payment=1, client=1, db=None):
        return book_tickets(db or self.db, client, 99, "2026-11-25", "21:00:00",
                            quantity, payment)

    def state(self):
        return self.query("""
            SELECT s.tickets_sold, COUNT(p.purchase_id), COALESCE(SUM(p.ticket_sold), 0)
            FROM Schedule s LEFT JOIN Ticket_Purchase p
              ON p.room_id = s.room_id AND p.screening_date = s.screening_date
             AND p.screening_time = s.screening_time
            WHERE s.room_id = 99 AND s.screening_date = '2026-11-25'
              AND s.screening_time = '21:00:00'
            GROUP BY s.tickets_sold
        """)[0]

    def test_successful_booking(self):
        purchase_id, total = self.purchase()
        self.assertGreater(purchase_id, 8)
        self.assertEqual(total, Decimal("12.00"))
        self.assertEqual(self.state(), (10, 2, 10))

    def test_invalid_payment(self):
        for payment in (99999, 3):  # nonexistent, then owned by client 2
            with self.subTest(payment=payment):
                with self.assertRaisesRegex(BookingError, "Invalid payment"):
                    self.purchase(payment=payment)
                self.assertEqual(self.state(), (9, 1, 9))

    def test_too_many_or_nonpositive_tickets(self):
        for quantity in (2, 0, -1):
            with self.subTest(quantity=quantity):
                with self.assertRaises(BookingError):
                    self.purchase(quantity=quantity)
                self.assertEqual(self.state(), (9, 1, 9))

    def test_unknown_screening(self):
        with self.assertRaisesRegex(BookingError, "Screening not found"):
            book_tickets(self.db, 1, 99999, "2026-11-25", "21:00:00", 1, 1)
        self.assertEqual(self.state(), (9, 1, 9))

    def test_rollback_after_purchase_insert(self):
        # Test-only trigger makes the UPDATE fail after the INSERT has succeeded.
        self.query("""
            CREATE TRIGGER fail_sold_update BEFORE UPDATE ON Schedule
            FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Test failure'
        """)
        with self.assertRaisesRegex(mysql.connector.Error, "Test failure"):
            self.purchase()
        self.assertEqual(self.state(), (9, 1, 9))
        self.assertEqual(self.query("SELECT COUNT(*) FROM Ticket_Purchase")[0][0], 8)

    def test_concurrent_last_seat(self):
        # Briefly hold the winning transaction open so the other buyer competes.
        self.query("""
            CREATE TRIGGER slow_purchase BEFORE INSERT ON Ticket_Purchase
            FOR EACH ROW DO SLEEP(0.3)
        """)
        barrier = Barrier(2)

        def buyer(client, payment):
            db = mysql.connector.connect(**self.config)
            try:
                barrier.wait(timeout=10)
                try:
                    self.purchase(client=client, payment=payment, db=db)
                    return "success"
                except BookingError as err:
                    if "Not enough seats" not in str(err):
                        raise
                    return "sold out"
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(buyer, 1, 1)
            second = pool.submit(buyer, 2, 3)
            results = [first.result(timeout=20), second.result(timeout=20)]
        self.assertCountEqual(results, ["success", "sold out"])
        self.assertEqual(self.state(), (10, 2, 10))
        self.assertEqual(self.query("SELECT COUNT(*) FROM Ticket_Purchase")[0][0], 9)

    def test_pricing_and_multiple_tickets(self):
        # Exact second anniversary has no discount; the following day does.
        self.query("UPDATE Movies SET release_date = '2024-11-15' WHERE movie_id = 1")
        _, total = book_tickets(self.db, 1, 1, "2026-11-15", "15:30:00", 2, 1)
        self.assertEqual(total, Decimal("30.00"))
        self.query("UPDATE Movies SET release_date = '2024-11-14' WHERE movie_id = 1")
        cases = [(1, "2026-11-15", "15:30:00", "12.00"),
                 (2, "2026-11-15", "18:30:00", "14.40"),
                 (3, "2026-11-15", "19:30:00", "16.00"),
                 (4, "2026-11-16", "16:00:00", "18.40")]
        for room, day, time, price in cases:
            with self.subTest(room=room):
                _, total = book_tickets(self.db, 1, room, day, time, 1, 1)
                self.assertEqual(total, Decimal(price))

    def test_invalid_login(self):
        output = StringIO()
        with patch("builtins.input", side_effect=[
                "missing@example.com", "wrong", "carla.direnzo@email.it", "wrong",
                "carla.direnzo@email.it", "hash_pwd_1"]), redirect_stdout(output):
            result = login(self.db)
        self.assertEqual(result[1:], (1, "user"))
        self.assertEqual(output.getvalue().count("Wrong email or password"), 2)
        self.db.rollback()

    def test_invalid_and_overlapping_screening_rules(self):
        # Check each validation rule directly, in addition to the menu tests.
        base = {"ri": 1, "mi": 1, "ml": "English", "sd": "2026-11-15", "st": "10:00:00"}
        cases = [{"ri": 99999}, {"mi": 99999}, {"ml": "Unknown"},
                 {"st": "09:00:00"}, {"st": "23:00:00"}, {"st": "16:00:00"}]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertEqual(self.query(add_mov_screen_query, base | changes), 0)
        self.assertEqual(self.query(add_mov_screen_query, base), 1)

    def test_analytics_from_admin_menu(self):
        output = StringIO()
        with patch("builtins.input", side_effect=["4", "5"]), redirect_stdout(output):
            admin_menu(Admin(99, self.db))
        for expected in ["Parasite | 2 | 128.80", "Inception | 3 | 50.40",
                         "Dune: Part Two | 1 | 108.00", "Spirited Away | 0 | 0.00"]:
            self.assertIn(expected, output.getvalue())
        with redirect_stdout(StringIO()):
            rows = Admin(99, self.db).view_anal()
        self.assertEqual(len(rows), 9)
        self.assertEqual(sum(row[2] for row in rows), Decimal("331.20"))
        # A later report on the same connection must see another client's sale.
        other = mysql.connector.connect(**self.config)
        try:
            self.purchase(db=other)
        finally:
            other.close()
        with redirect_stdout(StringIO()):
            updated = Admin(99, self.db).view_anal()
        self.assertIn(("Dune: Part Two", 2, Decimal("120.00")), updated)

    def test_booking_from_client_menu_after_login(self):
        output = StringIO()
        with patch("builtins.input", side_effect=["carla.direnzo@email.it", "hash_pwd_1"]):
            with redirect_stdout(output):
                _, client_id, _ = login(self.db)
        with patch("builtins.input", side_effect=[
                "2", "99", "2026-11-25", "21:00", "1", "1", "5"]):
            with redirect_stdout(output):
                client_menu(Client(client_id, self.db))
        self.assertIn("confirmed: 1 ticket(s), EUR 12.00", output.getvalue())
        self.assertEqual(self.state(), (10, 2, 10))


if __name__ == "__main__":
    unittest.main(verbosity=2)
