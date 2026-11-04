import mysql.connector 
from mysql.connector import errorcode

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

cursor = db.cursor()

query = ("SELECT M.title, S.date_time, S.movie_language, T.t_id "
         "FROM Movies M "
         "JOIN Schedule S ON M.m_id = S.m_id "
         "JOIN Theaters T ON S.t_id = T.t_id "
         "WHERE M.title LIKE '%Inception%' "
         "ORDER BY S.date_time ASC;")

cursor.execute(query)

for (title) in cursor:
  print(title)