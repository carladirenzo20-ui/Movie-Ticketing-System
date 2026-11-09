from database import connector
from database import login
#from client import Client
#from client import client_menu

db = connector()
if db == None:
    raise SystemExit("Could not connect to the database.")

user_email, user_id, user_type = login(db)
print("Welcome back,", user_email,". Logged in as:", user_type)

# if user_type == "user":
#     user1 = Client(user_email, db)
#     client_menu(user1)
# else:
#     admin1 = Admin(user_email, db)
#     admin_menu(admin1)