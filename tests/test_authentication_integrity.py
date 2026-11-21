import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from mysql.connector import DatabaseError, IntegrityError

from test_parts_6_7 import MySQLTests
from database import login


class AuthenticationIntegrityTests(MySQLTests):
    def test_password_requires_exact_match(self):
        email = "admin@cinema.it"
        attempts = [email, "HASH_PWD_ADMIN", email, "hàsh_pwd_admin",
                    email, "hash_pwd_admin ", email, "hash_pwd_admin"]
        output = StringIO()
        with patch("builtins.input", side_effect=attempts) as prompts, redirect_stdout(output):
            result = login(self.db)

        self.assertEqual(result, (email, 99, "admin"))
        self.assertEqual(prompts.call_count, len(attempts))
        self.assertEqual(output.getvalue().count("Wrong email or password"), 3)

    def test_roles_reject_other_subtype_and_direct_reassignment(self):
        for sql in (
            "INSERT INTO Administrator (user_id) VALUES (1)",
            "INSERT INTO Client (user_id) VALUES (99)",
            "UPDATE Users SET account_role = 'admin' WHERE user_id = 1",
        ):
            with self.subTest(sql=sql):
                with self.assertRaises(IntegrityError):
                    self.query(sql)
                self.db.rollback()

    def test_client_address_is_required(self):
        for address in (None, "", " \t "):
            with self.subTest(address=address):
                with self.assertRaises(DatabaseError) as error:
                    self.query("UPDATE Users SET address = %s WHERE user_id = 1", (address,))
                self.assertEqual(error.exception.errno, 3819)
                self.db.rollback()

        self.assertEqual(self.query("UPDATE Users SET address = NULL WHERE user_id = 99"), 1)


if __name__ == "__main__":
    unittest.main()
