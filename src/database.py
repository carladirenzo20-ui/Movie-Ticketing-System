import os
import mysql.connector
from mysql.connector import errorcode


def connector():
    try:
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "root"),
            database=os.getenv("MYSQL_DATABASE", "cinema_db"),
            connection_timeout=5,
        )
    except ValueError:
        print("MYSQL_PORT must be a number.")
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("MySQL access denied. Set MYSQL_USER and MYSQL_PASSWORD for your installation.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database not found. Run schema.sql and data.sql first.")
        else:
            print("Could not connect to MySQL:", err)
    return None


user_id_mail_query = """
SELECT u.user_id,
       CASE WHEN a.user_id IS NOT NULL THEN 'admin'
            WHEN c.user_id IS NOT NULL THEN 'user' END AS user_type
FROM Users u
LEFT JOIN Administrator a ON a.user_id = u.user_id
LEFT JOIN Client c ON c.user_id = u.user_id
WHERE u.email = %(e)s AND u.password = %(p)s
"""


def login(db):
    cursor = db.cursor(buffered=True)
    try:
        while True:
            email = input("Enter your email: ").strip()
            pw = input("Enter your password: ")
            cursor.execute(user_id_mail_query, {"e": email, "p": pw})
            row = cursor.fetchone()
            db.rollback()
            if row is None or row[1] is None:
                print("Wrong email or password, try again.")
            else:
                user_id, user_type = row
                return email, user_id, user_type
    finally:
        db.rollback()
        cursor.close()
