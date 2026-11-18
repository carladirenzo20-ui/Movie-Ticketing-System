-- Part 4: five queries. This entire file runs in the MySQL client.
USE cinema_db;

-- QUERY 1: Search screenings by movie title (joins, filtering and ordering).
SET @title = 'Inception';
SELECT M.title, S.screening_date, S.screening_time, S.movie_language, T.room_id
FROM Movies M
JOIN Schedule S ON M.movie_id = S.movie_id
JOIN Theaters T ON S.room_id = T.room_id
WHERE M.title LIKE CONCAT('%', @title, '%')
ORDER BY S.screening_date ASC, S.screening_time ASC;

-- QUERY 2: Parameterized purchase history, also executed by Client.prev_purch.
-- Connector/Python template used in src/client.py (named parameter i):
-- SELECT tot_amount, ticket_sold, payment_type, screening_date, screening_time
-- FROM Ticket_Purchase WHERE client_id = %(i)s
-- ORDER BY screening_date DESC, screening_time DESC
-- The same query uses a native MySQL parameter below so this file is executable.
SET @client_id = 1;
PREPARE purchase_history FROM
    'SELECT tot_amount, ticket_sold, payment_type, screening_date, screening_time
     FROM Ticket_Purchase WHERE client_id = ?
     ORDER BY screening_date DESC, screening_time DESC';
EXECUTE purchase_history USING @client_id;
DEALLOCATE PREPARE purchase_history;

-- QUERY 3: Revenue by movie, including movies with no purchases.
-- The administrator analytic executes this three-table aggregate query.
SELECT M.title, COUNT(P.purchase_id) AS purchases,
       COALESCE(SUM(P.tot_amount), 0) AS revenue
FROM Movies M
LEFT JOIN Schedule S ON M.movie_id = S.movie_id
LEFT JOIN Ticket_Purchase P
    ON S.room_id = P.room_id
    AND S.screening_date = P.screening_date
    AND S.screening_time = P.screening_time
GROUP BY M.movie_id, M.title
ORDER BY revenue DESC;

-- QUERY 4: Remaining seats for upcoming screenings.
SELECT M.title, S.screening_date, S.screening_time, T.room_id, T.max_capacity,
       T.max_capacity - S.tickets_sold AS available_seats
FROM Schedule S
JOIN Movies M ON S.movie_id = M.movie_id
JOIN Theaters T ON S.room_id = T.room_id
WHERE S.screening_date >= CURRENT_DATE()
ORDER BY available_seats ASC, S.screening_date ASC, S.screening_time ASC;

-- QUERY 5: Clients who purchased more than one ticket (GROUP BY and HAVING).
SELECT U.name, SUM(P.ticket_sold) AS total_tickets, SUM(P.tot_amount) AS total_spent
FROM Users U
JOIN Ticket_Purchase P ON U.user_id = P.client_id
GROUP BY U.user_id, U.name
HAVING SUM(P.ticket_sold) > 1
ORDER BY total_spent DESC;
