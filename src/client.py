from datetime import datetime

class Client:
    def __init__(self, id, connector):
        self.id = id
        self.connector = connector

    def src_mov_screens(self):
        cursor = self.connector.cursor()
        print("Search based on preferences. If you want to leave a preference blank, press 'start\n")
        title = input("Enter the movie title'\n")
        genre = input("Enter the movie genre\n")
        language = input("Enter the movie language\n")
        date = input("Enter the screening date. Valid format: 'YYYYMMDD'\n")
        time = input("Enter the screening time. Valid format. 'hhmm'\n")
        try:
            if date != "":
                date = datetime.strptime(date, '%Y%m%d').date()
            if time != "":
                time = datetime.strptime(time+"00", "%H%M%S").time()
            query = src_mov_screens_query(title, genre, language, date, time)
            cursor.execute(query, {"t": title, "g": genre, "l": language, "sd": date, "st": time})
            return cursor.fetchall()
        except:
            print("Unexpected error in the query\n")

    def buy_tickets():
        pass

    def prev_purch(self):
        cursor = self.connector.cursor()
        try:
            cursor.execute(prev_purch_query, {"i": self.id})
            return cursor.fetchall()
        except:
            print("Unexpected error in the query\n")

    def pay_met(self):
        cursor = self.connector.cursor()
        function_pay = int(input("Select one of the following functions:\n1. View registered payment methods \n2. Delete registered payment methods \n3. Add new payment method \n4. Go back to menu"))

        #View registered payment methods
        if function_pay == 1:
            cursor.execute(view_pay_met_query, {"i": self.id})
            return cursor.fetchall()
        #Delete registered payment methods
        if function_pay == 2:
            try:
                pmi = input("Write the registered payment id you want to delete. To view your payment ids, go back and select 'View registered payment methods'")
                cursor.execute(del_pay_met_query, {"i": self.id, "pmi": pmi})
                self.connector.commit()
                print("Payment method deleted successfully\n")
            except:
                print("Deletion unsuccessful\n")
        #Add new payment method
        if function_pay == 3:
            pass
        #Go back to menu
        if function_pay == 4:
            pass

def client_menu(client):
    while True:
        function_menu = int(input("Select one of the following functions:\n1. Search movie screenings\n2. Buy tickets\n3. View previous purchases\n4. Manage payment methods\n5. Exit\n"))
        if function_menu == 1:
            print(client.src_mov_screens())
        if function_menu == 2:
            pass
        if function_menu == 3:
            print(client.prev_purch())
        if function_menu == 4:
            print(client.pay_met())
        if function_menu == 5:
            break
        
prev_purch_query = (
    "SELECT tot_amount, ticket_sold, payment_type, screening_date, screening_time "
    "FROM ticket_purchase "
    "WHERE client_id = %(i)s "
    "ORDER BY screening_date DESC;"
)

view_pay_met_query = (
    "SELECT payment_type, card_number, billing_address, expiring_date "
    "FROM  payment_method "
    "WHERE client_id = %(i)s;"
)

del_pay_met_query = (
    "DELETE "
    "FROM payment_method "
    "WHERE client_id = %(i)s "
    "AND p_method_id = %(pmi)s "
)

add_pay_met_query = (
    "INSERT "
)

def src_mov_screens_query(mov_tit, genre, language, date, time):
    #DA INSERIRE TICKET PRICE E CAPIRE AVAILABLE SEATS COME FARLO DECRESCERE
    query = (
        "SELECT m.title, g.genre, s.room_id, s.screening_date, s.screening_time, s.movie_language, t.max_capacity, t.is_3D, t.premium_sound "
        "FROM movies m, schedule s, theaters t, movie_genres g "
        "WHERE m.movie_id = s.movie_id AND s.room_id = t.room_id and g.movie_id = m.movie_id "
    )   
    if mov_tit != "":
        query = query + "AND m.title = %(t)s "
    if genre != "":
        query = query + "And g.genre = %(g)s "
    if language != "":
        query = query + "And s.movie_language = %(l)s "
    if date != "":
        query = query + "And s.screening_date = %(sd)s "
    if time != "":
        query = query + "And s.screening_time = %(st)s "
    return query