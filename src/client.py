from datetime import datetime
from decimal import Decimal
from mysql.connector import Error

class BookingError(ValueError):
    """A purchase rejected because its details or available capacity are invalid."""

def book_tickets(db, client_id, room_id, screening_date, screening_time,
                 quantity, payment_method_id):
    """Return (purchase_id, total). The connection must have no open transaction."""
    if type(quantity) is not int or quantity <= 0:
        raise BookingError("The number of tickets must be a positive integer.")

    # Keep the transaction short: collect all user input before calling this function.
    db.start_transaction()
    cursor = None
    try:
        cursor = db.cursor(dictionary=True, buffered=True)
        screening_key = (room_id, screening_date, screening_time)

        # Always acquire the theater lock before the screening lock.
        cursor.execute("SELECT max_capacity FROM Theaters WHERE room_id = %s FOR UPDATE", (room_id,))
        theater = cursor.fetchone()
        if theater is None:
            raise BookingError("Screening not found.")

        # Only one buyer at a time can check and change this screening's sold count.
        cursor.execute("""
            SELECT tickets_sold, movie_id
            FROM Schedule
            WHERE room_id = %s AND screening_date = %s AND screening_time = %s
            FOR UPDATE
        """, screening_key)
        screening = cursor.fetchone()
        if screening is None:
            raise BookingError("Screening not found.")

        cursor.execute("""
            SELECT (15 + 5 * t.is_3D + 3 * t.premium_sound) *
                   CASE WHEN m.release_date < DATE_SUB(%s, INTERVAL 2 YEAR)
                        THEN 0.80 ELSE 1.00 END AS ticket_price
            FROM Theaters t CROSS JOIN Movies m
            WHERE t.room_id = %s AND m.movie_id = %s
        """, (screening_date, room_id, screening["movie_id"]))
        details = cursor.fetchone()
        available = theater["max_capacity"] - screening["tickets_sold"]
        if quantity > available:
            raise BookingError(f"Not enough seats: {available} remaining.")

        # A client can only pay with one of their own registered methods.
        cursor.execute("""
            SELECT payment_type
            FROM Payment_Method
            WHERE p_method_id = %s AND client_id = %s
        """, (payment_method_id, client_id))
        payment = cursor.fetchone()
        if payment is None:
            raise BookingError("Invalid payment method for this client.")

        total = (details["ticket_price"] * quantity).quantize(Decimal("0.01"))
        cursor.execute("""
            INSERT INTO Ticket_Purchase
                (tot_amount, ticket_sold, payment_type, client_id,
                 room_id, screening_date, screening_time, p_method_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (total, quantity, payment["payment_type"], client_id,
              *screening_key, payment_method_id))
        purchase_id = cursor.lastrowid

        cursor.execute("""
            UPDATE Schedule SET tickets_sold = tickets_sold + %s
            WHERE room_id = %s AND screening_date = %s AND screening_time = %s
        """, (quantity, *screening_key))
        db.commit()
        return purchase_id, total
    except Exception:
        # This also removes the purchase if the subsequent UPDATE fails.
        db.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()

def display_rows(headers, rows):
    print(" | ".join(headers))
    if not rows:
        print("No results.")
    for row in rows:
        print(" | ".join(str(value) for value in row))

class Client:
    def __init__(self, id, connector):
        self.id = id
        self.connector = connector

    def src_mov_screens(self):
        cursor = None
        try:
            print("Search screenings. Press Enter to skip any filter.")
            title = input("Movie title: ").strip()
            genre = input("Genre: ").strip()
            language = input("Language: ").strip()
            date = input("Date (YYYY-MM-DD): ").strip()
            time = input("Time (HH:MM): ").strip()
            if date:
                date = datetime.strptime(date.replace("-", ""), "%Y%m%d").date()
            if time:
                time = datetime.strptime(time.replace(":", ""), "%H%M").time()
            self.connector.rollback()
            cursor = self.connector.cursor(buffered=True)
            cursor.execute(src_mov_screens_query(title, genre, language, date, time),
                           {"t": title, "g": genre, "l": language, "sd": date, "st": time})
            rows = cursor.fetchall()
            display_rows(("Movie", "Theater", "Date", "Time", "Language", "Price (EUR)",
                          "Available seats", "3D", "Enhanced sound"), rows)
            return rows
        except ValueError:
            print("Invalid date or time. Use YYYY-MM-DD and HH:MM.")
            return []
        except Error as err:
            print("Could not search screenings:", err)
            return []
        finally:
            self.connector.rollback()
            if cursor is not None:
                cursor.close()

    def buy_tickets(self):
        cursor = None
        try:
            room_id = int(input("Theater ID: "))
            screening_date = datetime.strptime(input("Date (YYYY-MM-DD): "), "%Y-%m-%d").date()
            screening_time = datetime.strptime(input("Time (HH:MM): "), "%H:%M").time()
            quantity = int(input("Number of tickets: "))
            self.connector.rollback()
            cursor = self.connector.cursor(buffered=True)
            cursor.execute(
                "SELECT p_method_id, payment_type FROM Payment_Method WHERE client_id = %s",
                (self.id,),
            )
            methods = cursor.fetchall()
            if not methods:
                self.connector.rollback()
                print("Register a payment method before buying tickets.")
                return
            for method_id, payment_type in methods:
                print(f"{method_id}: {payment_type}")
            payment_method_id = int(input("Payment method ID: "))
            self.connector.rollback()
            purchase_id, total = book_tickets(
                self.connector, self.id, room_id, screening_date,
                screening_time, quantity, payment_method_id,
            )
            print(f"Purchase {purchase_id} confirmed: {quantity} ticket(s), EUR {total:.2f}.")
        except ValueError as err:
            self.connector.rollback()
            print(f"Purchase rejected: {err}")
        except Error as err:
            self.connector.rollback()
            print(f"Purchase failed: {err}")
        finally:
            if cursor is not None:
                cursor.close()

    def prev_purch(self):
        cursor = None
        try:
            self.connector.rollback()
            cursor = self.connector.cursor(buffered=True)
            cursor.execute(prev_purch_query, {"i": self.id})
            rows = cursor.fetchall()
            display_rows(("Total (EUR)", "Tickets", "Payment type", "Date", "Time"), rows)
            return rows
        except Error as err:
            print("Could not load purchase history:", err)
            return []
        finally:
            self.connector.rollback()
            if cursor is not None:
                cursor.close()

    def pay_met(self):
        while True:
            try:
                choice = int(input("1. View payment methods\n2. Delete payment method\n"
                                   "3. Add payment method\n4. Go back\n"))
                if choice in (1, 2, 3, 4):
                    break
            except ValueError:
                pass
            print("Choose a number from 1 to 4.")
        if choice == 4:
            return []
        cursor = None
        try:
            self.connector.rollback()
            cursor = self.connector.cursor(buffered=True)
            if choice == 1:
                cursor.execute(view_pay_met_query, {"i": self.id})
                rows = cursor.fetchall()
                display_rows(("ID", "Payment type", "Card/account", "Billing address", "Expiry"), rows)
                self.connector.rollback()
                return rows
            if choice == 2:
                method_id = int(input("Payment method ID to delete: "))
                cursor.execute(del_pay_met_query, {"i": self.id, "pmi": method_id})
                if cursor.rowcount == 0:
                    self.connector.rollback()
                    print("Payment method not found for this client.")
                    return []
                self.connector.commit()
                print("Payment method deleted successfully.")
            if choice == 3:
                payment_type = input("Payment type: ").strip()
                card_number = input("Card number or account reference: ").strip()
                billing_address = input("Billing address (Enter if not applicable): ").strip()
                expiry = datetime.strptime(input("Expiry date (YYYY-MM-DD): ").strip(), "%Y-%m-%d").date()
                if not payment_type or not card_number:
                    raise ValueError("Payment type and card/account reference are required.")
                cursor.execute(add_pay_met_query,
                               (self.id, payment_type, card_number, billing_address or None, expiry))
                method_id = cursor.lastrowid
                self.connector.commit()
                print(f"Payment method {method_id} added successfully.")
            return []
        except ValueError as err:
            self.connector.rollback()
            print("Invalid payment details:", err)
            return []
        except Error as err:
            self.connector.rollback()
            if err.errno == 1451:
                print("Cannot delete a payment method used by a previous purchase.")
            else:
                print("Payment operation failed:", err)
            return []
        finally:
            if cursor is not None:
                cursor.close()

def client_menu(client):
    while True:
        try:
            choice = int(input("1. Search movie screenings\n2. Buy tickets\n"
                               "3. View previous purchases\n4. Manage payment methods\n5. Exit\n"))
        except ValueError:
            print("Choose a number from 1 to 5.")
            continue
        if choice == 1:
            client.src_mov_screens()
        elif choice == 2:
            client.buy_tickets()
        elif choice == 3:
            client.prev_purch()
        elif choice == 4:
            client.pay_met()
        elif choice == 5:
            break
        else:
            print("Choose a number from 1 to 5.")

prev_purch_query = """
SELECT tot_amount, ticket_sold, payment_type, screening_date, screening_time
FROM Ticket_Purchase
WHERE client_id = %(i)s
ORDER BY screening_date DESC, screening_time DESC
"""

view_pay_met_query = """
SELECT p_method_id, payment_type, card_number, billing_address, expiring_date
FROM Payment_Method WHERE client_id = %(i)s ORDER BY p_method_id
"""

del_pay_met_query = """
DELETE FROM Payment_Method WHERE client_id = %(i)s AND p_method_id = %(pmi)s
"""

add_pay_met_query = """
INSERT INTO Payment_Method (client_id, payment_type, card_number, billing_address, expiring_date)
VALUES (%s, %s, %s, %s, %s)
"""

def src_mov_screens_query(mov_tit, genre, language, date, time):
    query = """
        SELECT m.title, s.room_id, s.screening_date, s.screening_time, s.movie_language,
               CAST((15 + 5 * t.is_3D + 3 * t.premium_sound) *
                    CASE WHEN m.release_date < DATE_SUB(s.screening_date, INTERVAL 2 YEAR)
                         THEN 0.80 ELSE 1.00 END AS DECIMAL(10,2)) AS ticket_price,
               t.max_capacity - s.tickets_sold AS available_seats, t.is_3D, t.premium_sound
        FROM Movies m JOIN Schedule s ON m.movie_id = s.movie_id
        JOIN Theaters t ON s.room_id = t.room_id
        WHERE 1 = 1
    """
    if mov_tit:
        query += " AND m.title LIKE CONCAT('%', %(t)s, '%')"
    if genre:
        query += " AND EXISTS (SELECT 1 FROM Movie_Genres g WHERE g.movie_id = m.movie_id AND g.genre = %(g)s)"
    if language:
        query += " AND s.movie_language = %(l)s"
    if date:
        query += " AND s.screening_date = %(sd)s"
    if time:
        query += " AND s.screening_time = %(st)s"
    return query + " ORDER BY s.screening_date, s.screening_time, s.room_id"
