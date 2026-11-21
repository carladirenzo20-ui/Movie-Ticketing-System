"""Part 6: one complete ticket purchase in a MySQL transaction."""

from decimal import Decimal


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

        # Acquire the room lock before the screening lock, as scheduling changes do.
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
