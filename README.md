# Movie Ticketing System

MySQL database and Python command-line application for cinema scheduling, ticket purchases, client payment methods and administrator analytics.

## Setup

Requirements: MySQL 8.0.16 or later, Python 3 and the package in `requirements.txt`. Run these commands from the project folder in PowerShell. If `.venv` already exists, skip its creation.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the MySQL command-line client from the project folder, using an account allowed to create the database:

```powershell
& 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe' -u root -p
```

Adjust that executable path if MySQL is installed elsewhere. At the MySQL prompt, create the tables and populate a fresh database:

```sql
SOURCE schema.sql;
SOURCE data.sql;
SOURCE queries.sql;
```

`queries.sql` runs the five demonstration queries after setup. Its example input values can be changed before execution. Run setup once against a fresh database; it does not reset an existing populated database.

The schema generates purchase and payment-method IDs automatically.

## Run the application

Configure the connection for your local MySQL account in the same PowerShell session, then run the application:

```powershell
$env:MYSQL_USER = 'root'
$env:MYSQL_PASSWORD = Read-Host 'MySQL password'
.\.venv\Scripts\python.exe src/main.py
```

The available connection variables and defaults are:

| Variable | Default |
| --- | --- |
| `MYSQL_HOST` | `localhost` |
| `MYSQL_PORT` | `3306` |
| `MYSQL_USER` | `root` |
| `MYSQL_PASSWORD` | `root` |
| `MYSQL_DATABASE` | `cinema_db` |

Set only the variables that differ on your computer. These settings select an existing MySQL account; they do not change its password.

Use these demonstration application accounts after loading `data.sql`:

| Role | Email | Password |
| --- | --- | --- |
| Client | `carla.direnzo@email.it` | `hash_pwd_1` |
| Client | `yara.messina@email.it` | `hash_pwd_2` |
| Administrator | `admin@cinema.it` | `hash_pwd_admin` |

The application retrieves each account's role from the database. Clients can search screenings, buy tickets, view purchases and manage payment methods. Administrators can add screenings, view the schedule and remaining capacity, and display revenue by movie.

## Design assumptions

- A cinema has multiple theaters. Each screening is identified by theater, date and start time; seats are sold as quantities without assigned seat numbers.
- `Users.user_id` is a surrogate identifier. Email remains unique. Each user has one account role. A client must have an address, and the client and administrator subtype rows must match the stored role.
- Every movie has a description and a primary genre. Additional genres are stored separately, and screening search uses the `Movie_Genres` view to read both. A screening's language must be available for its movie.
- The whole screening must fit between 10:00 and 23:59. A screening may start exactly when the previous one ends. MySQL validates screening writes and any runtime increase that could affect the schedule.
- Each screening stores its sold-ticket count. A booking changes this count and records the purchase in one transaction. MySQL rejects sold counts above capacity and capacity reductions below the sold count of any screening.
- Payment details belong to a client. A non-cash purchase must reference a registered method belonging to that client, with a matching payment type. Historical cash purchases record cash as the payment type. Methods referenced by purchases cannot be deleted.
- Card number, billing address and expiry date are single values per payment method. The ER diagram's `card_balance` is not maintained: this project records purchases without processing real payments or maintaining account balances.
- Ticket price is EUR 15, plus EUR 5 for 3D and EUR 3 for enhanced sound. A movie released more than two calendar years before the screening gets a 20% discount on the complete ticket price; exactly two years does not qualify. Purchases store the total charged at purchase time.
- Data and credentials are synthetic classroom examples. Values such as `hash_pwd_1` are literal, case-sensitive demonstration passwords.

## SQL queries

`queries.sql` contains screening search, a client's purchase history, movie revenue, remaining seats and clients who bought multiple tickets. Together they cover joins, filters, ordering, aggregation and `HAVING`. The purchase-history query includes its parameterized Python form and an executable MySQL prepared-statement demonstration.

## Booking and testing

The transaction and last-seat demonstration are explained below.

Run the automated checks against a running MySQL server using the connection variables above:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests create and remove uniquely named test databases instead of changing `cinema_db`. The test account needs permission to create and drop databases, create tables, views, routines and triggers, and execute the screening validation routine. The suite covers authentication, required records, screening validation, payment management, pricing, booking rollback, concurrent writes and analytics.

All 30 tests passed on MySQL 8.0.46 with Connector/Python 9.0.0 and 26.10.0. The MySQL client ran the setup and all five queries. Two independent application processes completed the last-seat demonstration with one successful purchase and one sold-out rejection.

## Part 6: booking transaction

Client menu option 2 collects the screening, ticket quantity and a registered payment-method ID. New bookings use a payment method belonging to the logged-in client; historical cash purchases in the seed data remain valid.

`book_tickets` in `src/booking.py` performs the following steps:

1. Start a MySQL transaction.
2. Lock the theater row, then the selected `Schedule` row, with `SELECT ... FOR UPDATE`.
3. Check remaining capacity and payment ownership, and calculate the total.
4. Insert the purchase.
5. Increase `tickets_sold`.
6. Commit both changes on success, or roll back on failure.

The function expects no existing transaction; the client interface ends its earlier read transaction before calling it. User input is collected before the booking transaction starts so the lock is held only while checking and recording the purchase.

The ticket price starts at EUR 15, adds EUR 5 for 3D and EUR 3 for enhanced sound, then applies a 20% discount to the complete price when the release date is strictly earlier than the screening date minus two calendar years. Exactly two years does not qualify. The total is the ticket price multiplied by quantity.

The theater lock keeps capacity stable and lets bookings acquire locks in the same order as new screenings. The screening lock protects the row that controls availability and provides the current sold count. A second buyer checks availability only after the first transaction commits or rolls back.

### Manual last-seat demonstration

Use a fresh copy of the seed database. Room 99 on **2026-11-25 at 21:00** has capacity 10 and 9 tickets sold.

1. Start two application instances in separate terminals using the connection settings above.
2. Log in as `carla.direnzo@email.it` / `hash_pwd_1` in one, and `yara.messina@email.it` / `hash_pwd_2` in the other.
3. In each instance, choose **Buy tickets**, room `99`, date `2026-11-25`, time `21:00`, quantity `1`.
4. Use payment ID `1` for Carla and `3` for Yara. Submit the final inputs close together.
5. Verify one confirmation, one capacity rejection, `tickets_sold = 10`, and only one additional purchase for this screening. It should have two purchase rows in total, including the original seed purchase.

Use a fresh test copy before repeating the demonstration; the successful purchase consumes the final seat. The automated test provides a repeatable alternative with two independent connections and a temporary database.

## Part 7: analytics and application tests

Administrator menu option 4 displays revenue and purchase counts by movie. Its query joins `Movies`, `Schedule` and `Ticket_Purchase`, groups by movie, and uses `COUNT` and `SUM`. `LEFT JOIN` and `COALESCE` include movies with no purchases and display zero revenue.

On untouched seed data, the movies with purchases have these results:

| Movie | Purchases | Revenue (EUR) |
| --- | ---: | ---: |
| Dune: Part Two | 1 | 144.00 |
| Parasite | 2 | 100.80 |
| Inception | 3 | 50.40 |
| Avatar: The Way of Water | 1 | 32.00 |
| Interstellar | 1 | 12.00 |

All other movies, including the recent synthetic movie **The Last Lantern**, have zero purchases and zero revenue. Total seed revenue is **EUR 339.20**. New bookings change these results. The Last Lantern screening in room 1 on **2026-11-23 at 16:00** costs EUR 15 per ticket and demonstrates undiscounted pricing.

The required cases and their expected outcomes are:

| Check | Expected result |
| --- | --- |
| Wrong login credentials | Login rejected; credentials requested again. |
| Unknown payment ID, or another client's ID | Purchase rejected; no purchase or sold-count change. |
| Request two tickets when one remains | Purchase rejected; no purchase or sold-count change. |
| Add a screening with an unknown movie/room, unavailable language, or outside 10:00-23:59 including runtime | Screening rejected; no added schedule row. |
| Add an overlapping screening in the same theater | Screening rejected; no added schedule row. |
| Database failure after purchase insertion | Insert rolled back; sold count unchanged. |
| Two clients buy the last seat | One succeeds, one is rejected; final sold count 10 and only one added purchase. |

The rollback test creates a test-only trigger that makes the sold-count update fail after the purchase insert. It verifies that rollback removes the inserted purchase and leaves availability unchanged. The concurrency test uses two database connections, then checks sold count, purchase count and total tickets recorded for the screening.

Record the automated output and manual demonstration results for the final presentation. Be prepared to explain why the lock covers the capacity check and why both writes must share the same transaction.

## Group contributions

The allocation below records the division of work provided for this project.

| Work allocation | Contribution |
| --- | --- |
| Earlier group work | Parts 1-5: ER model, relational schema, data, SQL queries and initial application |
| This contribution | Parts 6-7: booking transaction, concurrency demonstration, analytics and testing; integration and fixes to the earlier application |

## Project files

`ER_diagram.pdf` is the group's supplied ER diagram. `schema.sql`, `data.sql` and `queries.sql` are the database deliverables. `src/` contains the application and booking transaction. `tests/` contains the automated checks.
