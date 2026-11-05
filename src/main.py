from database import connector
from database import login

db = connector()
if db == None:
    raise SystemExit("Could not connect to the database.")

user_email, user_type = login(db)
print("Welcome back,", user_email,". Logged in as:", user_type)

if user_type == "user":
    user1 = Client(user_email, db)
else:
    admin1 = Admin(user_email, db)
