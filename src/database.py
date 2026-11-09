import mysql.connector 
from mysql.connector import errorcode

def connector():
  try:
      db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="cinema_db",
      )
  except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
      print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
      print("Database does not exist")
    else:
      print(err)
    return None
  return db

user_id_mail_query = (
  "SELECT u.user_id, "
  "  CASE WHEN a.user_id IS NOT NULL THEN 'admin' "
  "       WHEN c.user_id IS NOT NULL THEN 'user' "
  "  END AS user_type "
  "FROM Users u "
  "LEFT JOIN Administrator a ON a.user_id = u.user_id "
  "LEFT JOIN Client c ON c.user_id = u.user_id "
  "WHERE u.email = %(e)s AND u.password = %(p)s"
)

def login(db):
  print("running new login")
  cursor = db.cursor()
  while True:
    email = input("Enter your email: ")
    pw = input("Enter your password: ")
    cursor.execute(user_id_mail_query, {"e": email, "p": pw})
    row = cursor.fetchone()
    if row is None or row[1] is None:
      print("Wrong email or password, try again.")
    else:
      user_id, user_type = row
      return(email, user_id, user_type)