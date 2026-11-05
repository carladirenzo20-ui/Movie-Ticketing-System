function = str(input("Select one of the following functions:\n1. Search movie screenings\n2. Buy tickets\n3. View previous purchases\n4. Manage payment methods\n5. Exit\n"))

class Client:
    def __init__(self, email, connector):
        self.email = email
        self.connector = connector
    def src_mov_screens(self):
        pass
    def prev_purch(self):
        cursor = self.connector.cursor()
        try:
            cursor.execute(prev_purch_query, self.email)
        except:
            








prev_purch_query = (
    "SELECT U.name, M.title, P.ticket_sold, P.tot_amount, S.date_time "
    "FROM Users U "
    "JOIN Ticket_Purchase P ON U.email = P.client_email "
    "JOIN Schedule S ON P.t_id = S.t_id AND P.date_time = S.date_time "
    "JOIN Movies M ON S.m_id = M.m_id "
    "WHERE U.email = %(e)s "
    "ORDER BY S.date_time DESC; "
)
