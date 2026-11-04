from database import connector
from database import login

db = connector()
if db == None:
    raise SystemExit("Could not connect to the database.")

cursor = db.cursor()

user_type = login(cursor)
print("Logged in as:", user_type)