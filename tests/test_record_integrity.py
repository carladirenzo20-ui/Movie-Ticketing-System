from mysql.connector import DatabaseError

from test_parts_6_7 import MySQLTests


class RecordIntegrityTests(MySQLTests):
    def assert_rejected(self, sql, params, errno):
        with self.assertRaises(DatabaseError) as error:
            self.query(sql, params)
        self.assertEqual(error.exception.errno, errno)
        self.db.rollback()

    def test_movie_requires_description_and_primary_genre(self):
        updates = [
            ("description", None, 1048),
            ("description", " \t ", 3819),
            ("primary_genre", None, 1048),
            ("primary_genre", " \t ", 3819),
        ]
        for column, value, errno in updates:
            with self.subTest(column=column, value=value):
                self.assert_rejected(f"UPDATE Movies SET {column} = %s WHERE movie_id = 1",
                                     (value,), errno)

        genres = "SELECT genre FROM Movie_Genres WHERE movie_id = 1 ORDER BY genre"
        self.assertEqual(self.query(genres), [("Science Fiction",), ("Thriller",)])
        self.query("DELETE FROM Movie_Additional_Genres WHERE movie_id = 1")
        self.assertEqual(self.query(genres), [("Science Fiction",)])

    def test_purchase_identifies_method_or_records_cash(self):
        updates = [
            ("UPDATE Ticket_Purchase SET p_method_id = NULL WHERE purchase_id = 1", 3819),
            ("UPDATE Ticket_Purchase SET p_method_id = 3 WHERE purchase_id = 1", 1452),
            ("UPDATE Ticket_Purchase SET payment_type = 'PayPal' WHERE purchase_id = 1", 1452),
            ("UPDATE Ticket_Purchase SET payment_type = 'Credit Card' WHERE purchase_id = 7", 3819),
        ]
        for sql, errno in updates:
            with self.subTest(sql=sql):
                self.assert_rejected(sql, (), errno)

        self.assertEqual(self.query("""
            SELECT purchase_id, payment_type
            FROM Ticket_Purchase WHERE p_method_id IS NULL
        """), [(7, "Cash")])
