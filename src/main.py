from mysql.connector import Error
from database import connector, login
from client import Client, client_menu
from admin import Admin, admin_menu


def main():
    db = connector()
    if db is None:
        raise SystemExit("Could not connect to the database.")
    try:
        user_email, user_id, user_type = login(db)
        print("Welcome back,", user_email, ". Logged in as:", user_type)
        if user_type == "user":
            client_menu(Client(user_id, db))
        elif user_type == "admin":
            admin_menu(Admin(user_id, db))
    except Error as err:
        db.rollback()
        print("Database operation failed:", err)
    except (EOFError, KeyboardInterrupt):
        db.rollback()
        print("\nGoodbye.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
