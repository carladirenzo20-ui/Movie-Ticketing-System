class Client:
    def __init__(self, email, connector):
        self.email = email
        self.connector = connector

    def src_mov_screens(self):
        pass

    def prev_purch(self):
        cursor = self.connector.cursor()
        try:
            cursor.execute(prev_purch_query, {"e": self.email})
            return cursor.fetchone()
        except:
            print("Unexpected error in the query")

    def pay_met(self):
        cursor = self.connector.cursor()
        function_pay = int(input("Select one of the following functions:\n1. View registered payment methods \n2. Delete registered payment methods \n3. Add new payment method \n4. Go back to menu"))

        if function_pay == 1:
            cursor.execute(view_pay_met_query, {"e": self.email})
            print(cursor.fetchone())











def client_menu(client):
    while True:
        function_menu = int(input("Select one of the following functions:\n1. Search movie screenings\n2. Buy tickets\n3. View previous purchases\n4. Manage payment methods\n5. Exit\n"))
        if function_menu == 1:
            pass
        if function_menu == 2:
            pass
        if function_menu == 3:
            print(client.prev_purch())
        if function_menu == 4:
            client.pay_met()
        if function_menu == 5:
            break









prev_purch_query = (
    "SELECT U.name, M.title, P.ticket_sold, P.tot_amount, S.date_time "
    "FROM Users U "
    "JOIN Ticket_Purchase P ON U.email = P.client_email "
    "JOIN Schedule S ON P.t_id = S.t_id AND P.date_time = S.date_time "
    "JOIN Movies M ON S.m_id = M.m_id "
    "WHERE U.email = %(e)s "
    "ORDER BY S.date_time DESC; "
)

view_pay_met_query = (
    "SELECT card_number, billing_address, expiring_date "
    "FROM  payment_method "
    "WHERE client_registration = %(e)s;"
)
del_pay_met_query = ()
add_pay_met_query = ()
def src_mov_screens_query(mov_tit: str = None, genre: str = None, language: str = None, date, time):
    #DA INSERIRE TICKET PRICE E CAPIRE AVAILABLE SEATS COME FARLO DECRESCERE
    query = (
        "SELECT m.title, s.t_id, s.date_time, s.movie_language, t.max_capacity, t.is_3D, t.premium_sound "
        "FROM movies m, schedule s, theaters t "
        "WHERE m.m_id = s.m_id AND s.t_id = t.t_id "
    )   