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

user_type_query = (
  "SELECT "
  "CASE "
  "WHEN EXISTS (SELECT 1 FROM administrator a join users u on a.email = u.email WHERE u.email = %(e)s and password = %(p)s) THEN 'admin' "
  "WHEN EXISTS (SELECT 1 FROM client c join users u on c.email = u.email WHERE u.email = %(e)s and password = %(p)s) THEN 'user' "
  "ELSE NULL "
  "END as user_type; ")

def login(cursor):
  user_type = None
  while user_type == None:
    email = input("Enter your email: ")
    pw = input("Enter your password: ")
    cursor.execute(user_type_query, {"e": email, "p": pw})
    user_type = cursor.fetchone()[0]
    if user_type == None:
      print("Wrong email or password, try again.")
  return(user_type)