from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event

import mysql.connector

from test_parts_6_7 import MySQLTests, add_mov_screen_query


class ScheduleIntegrityTests(MySQLTests):
    def test_database_rejects_sold_count_above_capacity(self):
        for statement, message in [
            ("UPDATE Schedule SET tickets_sold = 11 WHERE room_id = 99",
             "Tickets sold cannot exceed theater capacity"),
            ("UPDATE Theaters SET max_capacity = 8 WHERE room_id = 99",
             "The new capacity is less than the tickets already sold"),
        ]:
            with self.subTest(statement=statement):
                with self.assertRaisesRegex(mysql.connector.Error, message):
                    self.query(statement)
                self.db.rollback()

    def test_opening_hours_adjacent_screenings_and_runtime_updates(self):
        base = {"ri": 1, "sd": "2026-11-30", "ml": "English", "mi": 1}
        for time in ("10:00:00", "12:28:00", "21:31:00"):
            self.assertEqual(self.query(add_mov_screen_query, base | {"st": time}), 1)

        for statement, message in [
            ("UPDATE Schedule SET screening_time = '12:27:00' "
             "WHERE room_id = 1 AND screening_date = '2026-11-30' AND screening_time = '12:28:00'",
             "overlapping screening"),
            ("UPDATE Movies SET running_time = 149 WHERE movie_id = 1",
             "exceed the cinema closing time"),
        ]:
            with self.subTest(statement=statement):
                with self.assertRaisesRegex(mysql.connector.Error, message):
                    self.query(statement)
                self.db.rollback()

        self.query("DELETE FROM Schedule WHERE room_id = 1 AND screening_date = '2026-11-30' "
                   "AND screening_time = '21:31:00'")
        with self.assertRaisesRegex(mysql.connector.Error, "make screenings overlap"):
            self.query("UPDATE Movies SET running_time = 149 WHERE movie_id = 1")
        self.db.rollback()
        self.assertEqual(self.query("UPDATE Movies SET running_time = 147 WHERE movie_id = 1"), 1)

    def test_concurrent_admin_inserts_cannot_overlap(self):
        for isolation, day in [("REPEATABLE READ", "2026-11-28"), ("READ COMMITTED", "2026-11-29")]:
            with self.subTest(isolation=isolation):
                params = {"ri": 1, "sd": day, "st": "12:00:00", "ml": "English", "mi": 1}
                ready = Event()

                def competing_insert():
                    with mysql.connector.connect(**self.config) as connection:
                        connection.start_transaction(isolation_level=isolation)
                        with connection.cursor() as cursor:
                            ready.set()
                            cursor.execute(add_mov_screen_query, params | {"st": "13:00:00"})
                            connection.commit()

                self.db.start_transaction(isolation_level=isolation)
                with self.db.cursor() as cursor, ThreadPoolExecutor(max_workers=1) as pool:
                    cursor.execute(add_mov_screen_query, params)
                    other = pool.submit(competing_insert)
                    try:
                        self.assertTrue(ready.wait(5))
                        with self.assertRaises(TimeoutError):
                            other.result(timeout=0.5)
                        self.db.commit()
                    finally:
                        self.db.rollback()
                    with self.assertRaisesRegex(mysql.connector.Error, "overlapping screening"):
                        other.result(timeout=5)

                self.assertEqual(self.query("""
                    SELECT CAST(screening_time AS CHAR) FROM Schedule
                    WHERE room_id = 1 AND screening_date = %s
                """, (day,)), [("12:00:00",)])
