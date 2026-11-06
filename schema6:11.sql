-- RESET DATABASE
DROP DATABASE IF EXISTS cinema_db;
CREATE DATABASE cinema_db;
USE cinema_db;

-- -----------------------------------------------------------------------------
-- STEP 2: SCHEMA DEFINITION
-- -----------------------------------------------------------------------------

-- 1) Users
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    address VARCHAR(100),
    name VARCHAR(100) NOT NULL
);

-- 2) Client (ISA from Users)
CREATE TABLE Client (
    user_id INT PRIMARY KEY,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE RESTRICT
);

-- 3) Administrator (ISA from Users)
CREATE TABLE Administrator (
    user_id INT PRIMARY KEY,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE RESTRICT
);

-- 4) Payment Method (Con indice/chiave univoca composta per il controllo di proprietà)
CREATE TABLE Payment_Method (
    p_method_id INT,
    client_id INT NOT NULL,
    payment_type VARCHAR(50) NOT NULL,
    card_number VARCHAR(50) NOT NULL,
    billing_address VARCHAR(100),
    expiring_date DATE NOT NULL,
    PRIMARY KEY (p_method_id),
    UNIQUE (p_method_id, client_id),
    FOREIGN KEY (client_id) REFERENCES Client(user_id) ON DELETE RESTRICT
);

-- 5) Theaters
CREATE TABLE Theaters (
    room_id INT PRIMARY KEY,
    max_capacity INT NOT NULL,
    is_3D BOOLEAN NOT NULL DEFAULT FALSE,
    premium_sound BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (max_capacity > 0)
);

-- 6) Movies
CREATE TABLE Movies (
    movie_id INT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    release_date DATE NOT NULL,
    running_time INT NOT NULL,
    description TEXT,
    original_language VARCHAR(100) NOT NULL,
    CHECK (running_time > 0)
);

-- 7) Movie Genres
CREATE TABLE Movie_Genres (
    movie_id INT NOT NULL,
    genre VARCHAR(100) NOT NULL,
    PRIMARY KEY (movie_id, genre),
    FOREIGN KEY (movie_id) REFERENCES Movies(movie_id) ON DELETE CASCADE
);

-- 8) Movie Available Languages
CREATE TABLE Movie_Languages (
    movie_id INT NOT NULL,
    available_language VARCHAR(100) NOT NULL,
    PRIMARY KEY (movie_id, available_language),
    FOREIGN KEY (movie_id) REFERENCES Movies(movie_id) ON DELETE CASCADE
);

-- 9) Schedule
CREATE TABLE Schedule (
    room_id INT NOT NULL,
    screening_date DATE NOT NULL,
    screening_time TIME NOT NULL,
    movie_language VARCHAR(100) NOT NULL,
    movie_id INT NOT NULL,
    tickets_sold INT NOT NULL DEFAULT 0,

    PRIMARY KEY (room_id, screening_date, screening_time),

    FOREIGN KEY (room_id) REFERENCES Theaters(room_id) ON DELETE RESTRICT,
    FOREIGN KEY (movie_id) REFERENCES Movies(movie_id) ON DELETE RESTRICT,
    FOREIGN KEY (movie_id, movie_language) REFERENCES Movie_Languages(movie_id, available_language) ON DELETE RESTRICT,
    
    CHECK (tickets_sold >= 0)
);

-- 10) Ticket Purchase (Con correzione ON DELETE RESTRICT sulla FK composta)
CREATE TABLE Ticket_Purchase (
    purchase_id INT PRIMARY KEY,
    tot_amount DECIMAL(10,2) NOT NULL,
    ticket_sold INT NOT NULL,
    payment_type VARCHAR(50) NOT NULL,
    client_id INT NOT NULL,
    room_id INT NOT NULL,
    screening_date DATE NOT NULL,
    screening_time TIME NOT NULL,
    p_method_id INT NULL,

    FOREIGN KEY (client_id) REFERENCES Client(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (room_id, screening_date, screening_time) REFERENCES Schedule(room_id, screening_date, screening_time) ON DELETE RESTRICT,
    FOREIGN KEY (p_method_id, client_id) REFERENCES Payment_Method(p_method_id, client_id) ON DELETE RESTRICT,

    CHECK (ticket_sold > 0),
    CHECK (tot_amount >= 0)
);

-- Indici di prestazione
CREATE INDEX idx_movies_title ON Movies(title);
CREATE INDEX idx_schedule_datetime ON Schedule(screening_date, screening_time);


-- -----------------------------------------------------------------------------
-- STEP 3: TEST DATA POPULATION
-- -----------------------------------------------------------------------------

USE cinema_db;

-- 1) Users
INSERT INTO Users (user_id, email, password, address, name) VALUES
(1, 'carla.direnzo@email.it', 'hash_pwd_1', 'Via Roma 10, Roma', 'Carla Direnzo'),            
(2, 'yara.messina@email.it', 'hash_pwd_2', 'Corso Italia 22, Milano', 'Yara Messina'),       
(3, 'alessandro.vertunni@email.it', 'hash_pwd_3', 'Via Etnea 45, Catania', 'Alessandro Vertunni'), 
(4, 'gabriele.agosta@email.it', 'hash_pwd_4', 'Via Toledo 12, Napoli', 'Gabriele Agosta'),   
(5, 'eleonora.raimondo@email.it', 'hash_pwd_5', 'Via Zamboni 5, Bologna', 'Eleonora Raimondo'), 
(6, 'lorenzo.pazienza@email.it', 'hash_pwd_6', 'Via Po 8, Torino', 'Lorenzo Pazienza'),       
(7, 'franco.moreno@email.it', 'hash_pwd_7', 'Via Dante 15, Firenze', 'Franco Moreno'),       
(8, 'carlo.soprano@email.it', 'hash_pwd_8', 'Via Toledo 20, Roma', 'Carlo Soprano'),         
(99, 'admin@cinema.it', 'hash_pwd_admin', 'Cinema Headquarters', 'Cinema Administrator');

-- 2) Clients
INSERT INTO Client (user_id) VALUES (1), (2), (3), (4), (5), (6), (7), (8);

-- 3) Administrator
INSERT INTO Administrator (user_id) VALUES (99);

-- 4) Payment Methods
INSERT INTO Payment_Method (p_method_id, client_id, payment_type, card_number, billing_address, expiring_date) VALUES
(1, 1, 'Credit Card', '4532-XXXX-XXXX-1111', 'Via Roma 10, Roma', '2028-12-31'),
(2, 1, 'PayPal', 'carla.paypal@email.it', 'Via Roma 10, Roma', '2029-01-31'), 
(3, 2, 'Credit Card', '5412-XXXX-XXXX-2222', 'Corso Italia 22, Milano', '2027-06-30'),
(4, 3, 'Apple Pay', '3782-XXXX-XXXX-3333', 'Via Etnea 45, Catania', '2029-01-31'),
(5, 4, 'Credit Card', '4000-XXXX-XXXX-4444', 'Via Toledo 12, Napoli', '2026-11-30'),
(6, 5, 'Google Pay', '5588-XXXX-XXXX-5588', 'Via Zamboni 5, Bologna', '2028-09-30'),
(7, 7, 'Credit Card', '4000-XXXX-XXXX-7777', 'Via Dante 15, Firenze', '2028-05-31');

-- 5) Theaters
INSERT INTO Theaters (room_id, is_3D, max_capacity, premium_sound) VALUES
(1, FALSE, 100, FALSE), 
(2, FALSE, 80, TRUE),   
(3, TRUE, 50, FALSE),   
(4, TRUE, 120, TRUE),   
(99, FALSE, 10, FALSE); 

-- 6) Movies
INSERT INTO Movies (movie_id, title, release_date, running_time, description, original_language) VALUES
(1, 'Inception', '2010-09-24', 148, 'A thief who steals corporate secrets through dreams.', 'English'),
(2, 'Avatar: The Way of Water', '2022-12-16', 192, 'Jake Sully lives with his newfound family.', 'English'),
(3, 'Parasite', '2019-11-07', 132, 'Two families from opposite social backgrounds.', 'Korean'),
(4, 'Amélie', '2001-04-25', 122, 'A young Parisian woman helps others.', 'French'),
(5, 'Interstellar', '2014-11-06', 169, 'A journey through a wormhole.', 'English'),
(6, 'Spirited Away', '2001-07-20', 125, 'A young girl enters a fantastic world.', 'Japanese'),
(7, 'Dune: Part Two', '2024-03-01', 166, 'Paul Atreides unites with the Fremen.', 'English'),
(8, 'Oppenheimer', '2023-07-21', 180, 'The story of J. Robert Oppenheimer.', 'English');

-- 7) Movie Genres
INSERT INTO Movie_Genres (movie_id, genre) VALUES
(1, 'Science Fiction'), (1, 'Thriller'),
(2, 'Sci-Fi'), (2, 'Adventure'),
(3, 'Thriller'), (3, 'Drama'),
(4, 'Comedy'), (4, 'Romance'),
(5, 'Science Fiction'), (5, 'Drama'),
(6, 'Animation'), (6, 'Fantasy'),
(7, 'Sci-Fi'), (7, 'Adventure'),
(8, 'Biography'), (8, 'Drama');

-- 8) Movie Available Languages
INSERT INTO Movie_Languages (movie_id, available_language) VALUES
(1, 'English'), (1, 'Italian'),
(2, 'English'), (2, 'Italian'),
(3, 'Korean'), (3, 'Italian'),
(4, 'French'), (4, 'Italian'),
(5, 'English'), (5, 'Italian'),
(6, 'Japanese'), (6, 'Italian'),
(7, 'English'), (7, 'Italian'),
(8, 'English'), (8, 'Italian');

-- 9) Schedule
INSERT INTO Schedule (room_id, screening_date, screening_time, movie_language, movie_id, tickets_sold) VALUES
(1, '2026-11-15', '15:30:00', 'English', 1, 3),
(2, '2026-11-15', '18:30:00', 'Italian', 1, 1),
(3, '2026-11-15', '19:30:00', 'English', 2, 2),
(4, '2026-11-16', '16:00:00', 'Korean', 3, 7),
(1, '2026-11-17', '17:00:00', 'English', 5, 1),
(99, '2026-11-25', '21:00:00', 'English', 7, 9),
(1, '2026-11-18', '16:00:00', 'English', 1, 0),
(2, '2026-11-18', '18:00:00', 'Italian', 7, 0),
(3, '2026-11-19', '14:00:00', 'English', 8, 0),
(4, '2026-11-19', '19:00:00', 'Italian', 2, 0),
(1, '2026-11-21', '18:00:00', 'Korean', 3, 0),
(2, '2026-11-22', '20:00:00', 'French', 4, 0);

-- 10) Ticket Purchases
INSERT INTO Ticket_Purchase (purchase_id, tot_amount, ticket_sold, payment_type, client_id, room_id, screening_date, screening_time, p_method_id) VALUES
(1, 24.00, 2, 'Credit Card', 1, 1, '2026-11-15', '15:30:00', 1),   
(2, 14.40, 1, 'PayPal', 1, 2, '2026-11-15', '18:30:00', 2),   
(3, 12.00, 1, 'Credit Card', 2, 1, '2026-11-15', '15:30:00', 3),   
(4, 32.00, 2, 'Credit Card', 2, 3, '2026-11-15', '19:30:00', 3),   
(5, 36.80, 2, 'Apple Pay', 3, 4, '2026-11-16', '16:00:00', 4),   
(6, 12.00, 1, 'Credit Card', 4, 1, '2026-11-17', '17:00:00', 5),   
(7, 92.00, 5, 'Cash', 6, 4, '2026-11-16', '16:00:00', NULL),
(8, 108.00, 9, 'Google Pay', 5, 99, '2026-11-25', '21:00:00', 6);


-- -----------------------------------------------------------------------------
-- STEP 4: QUERIES
-- -----------------------------------------------------------------------------
USE cinema_db;

-- QUERY 1: Search screenings by movie title (Per testare in workbench usa LIKE '%Inception%')
SELECT M.title, S.screening_date, S.screening_time, S.movie_language, T.room_id
FROM Movies M
JOIN Schedule S ON M.movie_id = S.movie_id
JOIN Theaters T ON S.room_id = T.room_id
WHERE M.title LIKE CONCAT('%', %s, '%')
ORDER BY S.screening_date ASC, S.screening_time ASC;

-- QUERY 2: Purchase history of a specific client
SELECT U.name, M.title, P.ticket_sold, P.tot_amount, S.screening_date, S.screening_time
FROM Users U
JOIN Ticket_Purchase P ON U.user_id = P.client_id
JOIN Schedule S ON P.room_id = S.room_id AND P.screening_date = S.screening_date AND P.screening_time = S.screening_time
JOIN Movies M ON S.movie_id = M.movie_id
WHERE U.user_id = 1
ORDER BY S.screening_date DESC;

-- QUERY 3: Total revenue generated by each movie
SELECT M.title, COUNT(P.purchase_id) AS purchases, COALESCE(SUM(P.tot_amount), 0) AS revenue
FROM Movies M
LEFT JOIN Schedule S ON M.movie_id = S.movie_id
LEFT JOIN Ticket_Purchase P 
    ON S.room_id = P.room_id 
    AND S.screening_date = P.screening_date 
    AND S.screening_time = P.screening_time
GROUP BY M.movie_id, M.title
ORDER BY revenue DESC;

-- QUERY 4: Remaining seats for each screening
SELECT M.title, S.screening_date, S.screening_time, T.room_id, T.max_capacity,
       T.max_capacity - COALESCE(S.tickets_sold, 0) AS available_seats
FROM Schedule S
JOIN Movies M ON S.movie_id = M.movie_id
JOIN Theaters T ON S.room_id = T.room_id
WHERE S.screening_date >= CURRENT_DATE()
ORDER BY available_seats ASC;

-- QUERY 5: Clients who purchased more than one ticket (HAVING)
SELECT U.name, SUM(P.ticket_sold) AS total_tickets, SUM(P.tot_amount) AS total_spent
FROM Users U
JOIN Ticket_Purchase P ON U.user_id = P.client_id
GROUP BY U.user_id, U.name
HAVING SUM(P.ticket_sold) > 1
ORDER BY total_spent DESC;