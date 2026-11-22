from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import mysql.connector

from test_parts_6_7 import MySQLTests
from admin import Admin
from client import BookingError, book_tickets


class ScheduleIntegrityTests(MySQLTests):
    def add_screening(self, db, time, *, room="1", day="2026-11-30"):
        with patch("builtins.input", side_effect=[room, "1", "English", day, time]), \
                redirect_stdout(StringIO()):
            return Admin(99, db).add_mov_screen()

    def test_booking_uses_current_theater_capacity(self):
        self.query("UPDATE Theaters SET max_capacity = 9 WHERE room_id = 99")
        with self.assertRaisesRegex(BookingError, "Not enough seats: 0 remaining"):
            book_tickets(self.db, 1, 99, "2026-11-25", "21:00:00", 1, 1)
        self.assertEqual(self.query("""
            SELECT tickets_sold FROM Schedule
            WHERE room_id = 99 AND screening_date = '2026-11-25'
        """), [(9,)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM Ticket_Purchase"), [(8,)])

    def test_opening_hours_adjacent_screenings_and_current_runtime(self):
        for time, accepted in [("09:59", False), ("10:00", True), ("12:27", False),
                               ("12:28", True), ("21:32", False), ("21:31", True)]:
            with self.subTest(time=time):
                self.assertIs(self.add_screening(self.db, time), accepted)
        self.assertEqual(self.query("""
            SELECT CAST(screening_time AS CHAR) FROM Schedule
            WHERE room_id = 1 AND screening_date = '2026-11-30'
            ORDER BY screening_time
        """), [("10:00:00",), ("12:28:00",), ("21:31:00",)])

        self.query("UPDATE Movies SET running_time = 147 WHERE movie_id = 1")
        self.assertTrue(self.add_screening(self.db, "21:32", day="2026-12-01"))

    def test_admin_rejects_overlap_with_committed_screening(self):
        self.assertTrue(self.add_screening(self.db, "12:00"))

        with mysql.connector.connect(**self.config) as other:
            self.assertFalse(self.add_screening(other, "11:00"))
            self.assertFalse(self.add_screening(other, "13:00"))
            self.assertTrue(self.add_screening(other, "13:00", room="2"))
            self.assertTrue(self.add_screening(other, "13:00", day="2026-12-01"))

        self.assertEqual(self.query("""
            SELECT CAST(screening_time AS CHAR) FROM Schedule
            WHERE room_id = 1 AND screening_date = '2026-11-30'
        """), [("12:00:00",)])
