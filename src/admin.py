from datetime import datetime
from mysql.connector import Error

class Admin:
    def __init__(self, id, connector):
        self.id = id
        self.connector = connector
    def add_mov_screen(self):
        cursor = None
        try:
            room_id = int(input("Room id: "))
            movie_id = int(input("Movie id: "))
            movie_language = input("Language: ").strip()
            screening_date = datetime.strptime(
                input("Date (YYYY-MM-DD): ").strip(), "%Y-%m-%d"
            ).date()
            screening_time = datetime.strptime(
                input("Time (HH:MM): ").strip(), "%H:%M"
            ).time()
            self.connector.rollback()
            cursor = self.connector.cursor()
            cursor.execute(add_mov_screen_query, {"ri": room_id, "sd": screening_date, "st": screening_time, "ml": movie_language, "mi": movie_id})
            if cursor.rowcount == 0:
                self.connector.rollback()
                print("Screening rejected. Check the movie ID, theater ID, and available language. "
                      "Screenings must fit between 10:00 and 23:59 and cannot overlap in the same theater.")
                return False
            self.connector.commit()
            print("Screening added.")
            return True
        except ValueError:
            self.connector.rollback()
            print("Invalid input: use numeric IDs, date YYYY-MM-DD and time HH:MM.")
            return False
        except Error as err:
            self.connector.rollback()
            print("Could not add screening:", err)
            return False
        finally:
            if cursor is not None:
                cursor.close()
        
    def screen_sched(self):
        cursor = None
        try:
            self.connector.rollback()
            cursor = self.connector.cursor()
            cursor.execute(screen_sched_query)
            rows = cursor.fetchall()
            self.connector.rollback()
            return rows
        except Error as err:
            self.connector.rollback()
            print("Could not load screening schedule:", err)
            return []
        finally:
            if cursor is not None:
                cursor.close()

    def remain_cap(self):
        cursor = None
        try:
            self.connector.rollback()
            cursor = self.connector.cursor()
            cursor.execute(remain_cap_query)
            rows = cursor.fetchall()
            self.connector.rollback()
            return rows
        except Error as err:
            self.connector.rollback()
            print("Could not load remaining capacity:", err)
            return []
        finally:
            if cursor is not None:
                cursor.close()

    def view_anal(self):
        cursor = None
        try:
            # End earlier menu reads so the report includes newly committed sales.
            self.connector.rollback()
            cursor = self.connector.cursor()
            cursor.execute(revenue_by_movie_query)
            rows = cursor.fetchall()
            self.connector.rollback()
            print("Movie | Purchases | Revenue (EUR)")
            for title, purchases, revenue in rows:
                print(f"{title} | {purchases} | {revenue:.2f}")
            return rows
        except Error as err:
            self.connector.rollback()
            print("Could not load analytics:", err)
            return []
        finally:
            if cursor is not None:
                cursor.close()

def admin_menu(admin):
    while True:
        try:
            function_menu = int(input("Select one of the following functions:\n1. Add a movie screening\n2. View the screening schedule\n3. View remaining capacity\n4. View analytics\n5. Exit\n"))
        except ValueError:
            print("Choose a number from 1 to 5.")
            continue
        if function_menu not in range(1, 6):
            print("Choose a number from 1 to 5.")
            continue
        if function_menu == 1:
            admin.add_mov_screen()
        if function_menu == 2:
            rows = admin.screen_sched()
            print("Movie | Theater | Date | Time | Language | Tickets sold")
            for row in rows:
                print(" | ".join(str(value) for value in row))
        if function_menu == 3:
            rows = admin.remain_cap()
            print("Movie | Theater | Date | Time | Capacity | Tickets sold | Available seats")
            for row in rows:
                print(" | ".join(str(value) for value in row))
        if function_menu == 4:
            admin.view_anal()
        if function_menu == 5:
            break

screen_sched_query = """
SELECT m.title, s.room_id, s.screening_date, s.screening_time,
       s.movie_language, s.tickets_sold
FROM Schedule s
JOIN Movies m ON m.movie_id = s.movie_id
ORDER BY s.screening_date, s.screening_time, s.room_id;
"""

remain_cap_query = """
SELECT m.title, s.room_id, s.screening_date, s.screening_time,
       t.max_capacity, s.tickets_sold,
       t.max_capacity - s.tickets_sold AS remaining_capacity
FROM Schedule s
JOIN Movies m ON m.movie_id = s.movie_id
JOIN Theaters t ON t.room_id = s.room_id
ORDER BY s.screening_date, s.screening_time, s.room_id;
"""

revenue_by_movie_query = """
SELECT M.title, COUNT(P.purchase_id) AS purchases,
       COALESCE(SUM(P.tot_amount), 0) AS revenue
FROM Movies M
LEFT JOIN Schedule S ON M.movie_id = S.movie_id
LEFT JOIN Ticket_Purchase P
    ON S.room_id = P.room_id
    AND S.screening_date = P.screening_date
    AND S.screening_time = P.screening_time
GROUP BY M.movie_id, M.title
ORDER BY revenue DESC;
"""

add_mov_screen_query = """
INSERT INTO Schedule (room_id, screening_date, screening_time, movie_language, movie_id)
SELECT t.room_id, %(sd)s, %(st)s, ml.available_language, m.movie_id
FROM Movies m
JOIN Movie_Languages ml ON ml.movie_id = m.movie_id AND ml.available_language = %(ml)s
JOIN Theaters t ON t.room_id = %(ri)s
WHERE m.movie_id = %(mi)s
  AND TIME(%(st)s) >= '10:00:00'
  AND TIMESTAMP(%(sd)s, %(st)s) + INTERVAL m.running_time MINUTE
        <= TIMESTAMP(%(sd)s, '23:59:00')
  AND NOT EXISTS (
      SELECT 1
      FROM Schedule s
      JOIN Movies existing_movie ON existing_movie.movie_id = s.movie_id
      WHERE s.room_id = t.room_id
        AND s.screening_date = %(sd)s
        AND TIMESTAMP(s.screening_date, s.screening_time)
            < TIMESTAMP(%(sd)s, %(st)s) + INTERVAL m.running_time MINUTE
        AND TIMESTAMP(s.screening_date, s.screening_time)
            + INTERVAL existing_movie.running_time MINUTE > TIMESTAMP(%(sd)s, %(st)s)
  )
"""
