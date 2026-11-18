"""Regression checks for the application fixes, using isolated MySQL databases."""

import os
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import Mock, patch

from test_parts_6_7 import MySQLTests
from admin import Admin, admin_menu
from client import Client, client_menu
from database import login
import database
import main as application


class ApplicationTests(MySQLTests):
    def call_with_input(self, function, answers):
        output = StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            result = function()
        return result, output.getvalue()

    def test_admin_menu_recovers_and_creates_screening(self):
        _, output = self.call_with_input(
            lambda: admin_menu(Admin(99, self.db)),
            ["bad", "8", "1", "1", "1", "English", "2026-11-15", "10:00", "5"],
        )
        self.assertEqual(output.count("Choose a number from 1 to 5."), 2)
        self.assertEqual(output.count("Screening added."), 1)
        self.assertNotIn("None", output)
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.query("""
            SELECT movie_id FROM Schedule
            WHERE room_id = 1 AND screening_date = '2026-11-15'
              AND screening_time = '10:00:00'
        """), [(1,)])

    def test_admin_rejects_invalid_inputs_and_screenings(self):
        admin = Admin(99, self.db)
        malformed = [["bad"], ["1", "bad"],
                     ["1", "1", "English", "bad-date"],
                     ["1", "1", "English", "2026-11-15", "25:00"]]
        rejected = [["99999", "1", "English", "2026-11-15", "10:00"],
                    ["1", "99999", "English", "2026-11-15", "10:00"],
                    ["1", "1", "Unknown", "2026-11-15", "10:00"],
                    ["1", "1", "English", "2026-11-15", "09:00"],
                    ["1", "1", "English", "2026-11-15", "23:00"],
                    ["1", "1", "English", "2026-11-15", "16:00"]]
        for answers in malformed + rejected:
            with self.subTest(answers=answers):
                result, output = self.call_with_input(admin.add_mov_screen, answers)
                self.assertIs(result, False)
                self.assertNotIn("Screening added.", output)
                self.assertIn("Invalid input" if answers in malformed else "Screening rejected", output)
                self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.query("SELECT COUNT(*) FROM Schedule"), [(13,)])

    def test_admin_rolls_back_database_error(self):
        # Change a validated movie ID inside a test trigger to cause a real FK error.
        self.query("""
            CREATE TRIGGER invalid_screening_movie BEFORE INSERT ON Schedule
            FOR EACH ROW SET NEW.movie_id = 99999
        """)
        result, output = self.call_with_input(
            Admin(99, self.db).add_mov_screen,
            ["1", "1", "English", "2026-11-15", "10:00"],
        )
        self.assertIs(result, False)
        self.assertIn("Could not add screening", output)
        self.assertIn("1452", output)
        self.assertNotIn("Screening added.", output)
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.query("SELECT COUNT(*) FROM Schedule"), [(13,)])

    def test_schedule_and_capacity_identify_screenings(self):
        admin = Admin(99, self.db)
        schedule = admin.screen_sched()
        self.assertFalse(self.db.in_transaction)
        capacity = admin.remain_cap()
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(len(schedule), 13)
        self.assertEqual(len(capacity), 13)
        self.assertIn(("Dune: Part Two", 99, date(2026, 11, 25),
                       timedelta(hours=21), "English", 9), schedule)
        self.assertIn(("Dune: Part Two", 99, date(2026, 11, 25),
                       timedelta(hours=21), 10, 9, 1), capacity)
        _, output = self.call_with_input(lambda: admin_menu(admin), ["2", "3", "5"])
        self.assertIn("Movie | Theater | Date | Time", output)
        self.assertIn("Capacity | Tickets sold | Available seats", output)
        self.assertIn("Dune: Part Two | 99 | 2026-11-25 | 21:00:00 | 10 | 9 | 1", output)

    def test_search_returns_distinct_complete_screenings_and_prices(self):
        rows, output = self.call_with_input(Client(1, self.db).src_mov_screens, [""] * 5)
        self.assertEqual(len(rows), 13)
        self.assertTrue(all(len(row) == 9 for row in rows))
        self.assertEqual(len({row[1:4] for row in rows}), 13)
        self.assertIn("Price (EUR) | Available seats | 3D | Enhanced sound", output)
        cases = [("Inception", 1, date(2026, 11, 15), "12.00", 97, 0, 0),
                 ("Inception", 2, date(2026, 11, 15), "14.40", 79, 0, 1),
                 ("Avatar: The Way of Water", 3, date(2026, 11, 15), "16.00", 48, 1, 0),
                 ("Parasite", 4, date(2026, 11, 16), "18.40", 113, 1, 1),
                 ("The Last Lantern", 1, date(2026, 11, 23), "15.00", 100, 0, 0)]
        for title, room, day, price, seats, is_3d, sound in cases:
            with self.subTest(title=title, room=room):
                row = next(row for row in rows if row[:3] == (title, room, day))
                self.assertEqual(row[5:], (Decimal(price), seats, is_3d, sound))
        self.assertFalse(self.db.in_transaction)

    def test_search_combines_filters_and_handles_bad_dates(self):
        client = Client(1, self.db)
        cases = [(["Inception", "", "", "", ""], 3),
                 (["", "Thriller", "", "", ""], 5),
                 (["Inception", "Thriller", "English", "2026-11-15", "15:30"], 1)]
        for answers, count in cases:
            with self.subTest(answers=answers):
                rows, _ = self.call_with_input(client.src_mov_screens, answers)
                self.assertEqual(len(rows), count)
                self.assertEqual(len({row[1:4] for row in rows}), count)
                self.assertFalse(self.db.in_transaction)
        for answers in [["", "", "", "bad-date", ""], ["", "", "", "", "25:00"]]:
            with self.subTest(answers=answers):
                rows, output = self.call_with_input(client.src_mov_screens, answers)
                self.assertEqual(rows, [])
                self.assertIn("Invalid date or time", output)
                self.assertFalse(self.db.in_transaction)

    def test_payment_add_view_ownership_and_delete(self):
        client = Client(1, self.db)
        _, output = self.call_with_input(client.pay_met,
                                        ["3", "Credit Card", "test-account", "", "2030-12-31"])
        self.assertIn("added successfully", output)
        self.assertFalse(self.db.in_transaction)
        method_id = self.query("""
            SELECT p_method_id FROM Payment_Method
            WHERE client_id = 1 AND card_number = 'test-account'
        """)[0][0]
        rows, output = self.call_with_input(client.pay_met, ["1"])
        self.assertIn("ID | Payment type", output)
        self.assertEqual({row[0] for row in rows}, {1, 2, method_id})
        self.assertIn((method_id, "Credit Card", "test-account", None, date(2030, 12, 31)), rows)
        other_rows, _ = self.call_with_input(Client(2, self.db).pay_met, ["1"])
        self.assertEqual({row[0] for row in other_rows}, {3})
        _, output = self.call_with_input(client.pay_met, ["2", str(method_id)])
        self.assertIn("Payment method deleted successfully", output)
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.query("SELECT COUNT(*) FROM Payment_Method WHERE p_method_id = %s",
                                    (method_id,)), [(0,)])

    def test_payment_failures_preserve_methods_and_end_transactions(self):
        client = Client(1, self.db)
        for method_id in (99999, 3):
            with self.subTest(method_id=method_id):
                _, output = self.call_with_input(client.pay_met, ["2", str(method_id)])
                self.assertIn("not found for this client", output)
                self.assertNotIn("deleted successfully", output)
                self.assertFalse(self.db.in_transaction)
        _, output = self.call_with_input(client.pay_met, ["2", "1"])
        self.assertIn("Cannot delete a payment method used by a previous purchase", output)
        self.assertNotIn("deleted successfully", output)
        self.assertFalse(self.db.in_transaction)
        invalid = [["2", "bad"], ["3", "Credit Card", "test-account", "", "bad-date"],
                   ["3", "", "test-account", "", "2030-12-31"]]
        for answers in invalid:
            with self.subTest(answers=answers):
                _, output = self.call_with_input(client.pay_met, answers)
                self.assertIn("Invalid payment details", output)
                self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.query("SELECT COUNT(*) FROM Payment_Method"), [(7,)])
        self.assertEqual(self.query("SELECT client_id FROM Payment_Method WHERE p_method_id = 3"), [(2,)])

    def test_client_and_payment_menus_recover_from_invalid_choices(self):
        _, output = self.call_with_input(lambda: client_menu(Client(1, self.db)),
                                        ["bad", "0", "4", "bad", "9", "1", "5"])
        self.assertEqual(output.count("Choose a number from 1 to 5."), 2)
        self.assertEqual(output.count("Choose a number from 1 to 4."), 2)
        self.assertIn("ID | Payment type", output)
        self.assertNotIn("None", output)
        self.assertFalse(self.db.in_transaction)

    def test_database_roles_control_main_menu_access(self):
        for email, password, user_id, role in [
                ("carla.direnzo@email.it", "hash_pwd_1", 1, "user"),
                ("admin@cinema.it", "hash_pwd_admin", 99, "admin")]:
            with self.subTest(role=role):
                credentials, _ = self.call_with_input(lambda: login(self.db), [email, password])
                self.assertEqual(credentials[1:], (user_id, role))
                self.assertFalse(self.db.in_transaction)
                connection = Mock()
                with patch.object(application, "connector", return_value=connection), \
                     patch.object(application, "login", return_value=credentials), \
                     patch.object(application, "client_menu") as clients, \
                     patch.object(application, "admin_menu") as admins, \
                     redirect_stdout(StringIO()):
                    application.main()
                selected, forbidden = (clients, admins) if role == "user" else (admins, clients)
                selected.assert_called_once()
                forbidden.assert_not_called()
                account = selected.call_args.args[0]
                self.assertEqual(account.id, user_id)
                self.assertIs(account.connector, connection)
                connection.close.assert_called_once()


class ConnectionSettingsTests(unittest.TestCase):
    def test_connection_uses_settings_and_rejects_invalid_port(self):
        settings = {"MYSQL_HOST": "db.example", "MYSQL_PORT": "3308", "MYSQL_USER": "student",
                    "MYSQL_PASSWORD": "test-only", "MYSQL_DATABASE": "class_project"}
        with patch.dict(os.environ, settings, clear=True), \
             patch.object(database.mysql.connector, "connect") as connect:
            self.assertIs(database.connector(), connect.return_value)
            connect.assert_called_once_with(host="db.example", port=3308, user="student",
                                            password="test-only", database="class_project",
                                            connection_timeout=5)
        with patch.dict(os.environ, {"MYSQL_PORT": "bad"}, clear=True), \
             patch.object(database.mysql.connector, "connect") as connect, \
             redirect_stdout(StringIO()) as output:
            self.assertIsNone(database.connector())
            connect.assert_not_called()
            self.assertIn("MYSQL_PORT must be a number", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
