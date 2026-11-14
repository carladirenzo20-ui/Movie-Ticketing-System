import datetime

class Admin:
    def __init__(self, id, connector):
        self.id = id
        self.connector = connector
    def add_mov_screen(self):
        cursor = self.connector.cursor()
        room_id = int(input("Room id: "))
        movie_id = int(input("Movie id: "))
        movie_language = input("Language: ")
        screening_date = datetime.strptime(
            input("Date (YYYY-MM-DD): "), "%Y-%m-%d"
        ).date()
        screening_time = datetime.strptime(
            input("Time (HH:MM): ").strip(), "%H:%M"
        ).time()
        try:
            cursor.execute(add_mov_screen_query, {"ri": room_id, "sd": screening_date, "st": screening_time, "ml": movie_language, "mi": movie_id})
            if cursor.rowcount == 0:
                self.connector.rollback()
                print("Screening rejected: unknown movie/room, language not available, "
                      "outside 10:00-23:59, or room already occupied.")
            self.connector.commit()
            print("Screening added.")
        except:
            print("Unexpected error in the query\n")
        
    def screen_sched(self):
        cursor = self.connector.cursor()
        cursor.execute(screen_sched_query)
        return cursor.fetchall() 
    def remain_cap(self):
        cursor = self.connector.cursor()
        cursor.execute(remain_cap_query)
        return cursor.fetchall()
    def view_anal(self):
        pass

def admin_menu(admin):
    while True:
        function_menu = int(input("Select one of the following functions:\n1. Add a movie screening\n2. View the screening schedule\n3. View remaining capacity\n4. View analytics\n5. Exit\n"))
        if function_menu == 1:
            print(admin.src_mov_screens())
        if function_menu == 2:
            print(admin.screen_sched())
        if function_menu == 3:
            print(admin.remain_cap())
        if function_menu == 4:
            pass
        if function_menu == 5:
            break
        
screen_sched_query = (
    "SELECT * "
    "FROM schedule;"
)

remain_cap_query = (
    "Select (t.max_capacity - s.tickets_sold) as remaining_capacity "
    "from theaters t, schedule s "
    "where s.room_id = t.room_id;"
)

add_mov_screen_query = """
INSERT INTO Schedule (room_id, screening_date, screening_time, movie_language, movie_id)
SELECT t.room_id, %(sd)s, %(st)s, mlang.available_language, m.movie_id
FROM Movies m
JOIN Movie_Languages mlang
       ON mlang.movie_id = m.movie_id
      AND mlang.available_language = %(ml)s            -- language available for the movie
JOIN Theaters t
       ON t.room_id = %(ri)s                           -- theater exists
WHERE m.movie_id = %(mi)s                              -- movie exists
  AND TIME(%(st)s) >= '10:00:00'                       -- not before opening
  AND TIMESTAMP(%(sd)s, %(st)s) + INTERVAL m.running_time MINUTE
        <= TIMESTAMP(%(sd)s, '23:59:00')               -- ends before closing
  AND NOT EXISTS (                                     -- no overlap in the same room
        SELECT 1
        FROM Schedule s
        JOIN Movies m2 ON m2.movie_id = s.movie_id
        WHERE s.room_id = t.room_id
          AND s.screening_date = %(sd)s
          AND TIMESTAMP(s.screening_date, s.screening_time)
                < TIMESTAMP(%(sd)s, %(st)s) + INTERVAL m.running_time MINUTE
          AND TIMESTAMP(s.screening_date, s.screening_time) + INTERVAL m2.running_time MINUTE
                > TIMESTAMP(%(sd)s, %(st)s)
  )
"""