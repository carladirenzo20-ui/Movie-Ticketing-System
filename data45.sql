-- Part 3: synthetic data. Run once after schema.sql.

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
(8, 'Oppenheimer', '2023-07-21', 180, 'The story of J. Robert Oppenheimer.', 'English'),
(9, 'The Last Lantern', '2026-10-01', 100, 'A synthetic recent-film fixture for undiscounted pricing.', 'English');

-- 7) Movie Genres
INSERT INTO Movie_Genres (movie_id, genre) VALUES
(1, 'Science Fiction'), (1, 'Thriller'),
(2, 'Sci-Fi'), (2, 'Adventure'),
(3, 'Thriller'), (3, 'Drama'),
(4, 'Comedy'), (4, 'Romance'),
(5, 'Science Fiction'), (5, 'Drama'),
(6, 'Animation'), (6, 'Fantasy'),
(7, 'Sci-Fi'), (7, 'Adventure'),
(8, 'Biography'), (8, 'Drama'),
(9, 'Drama');

-- 8) Movie Available Languages
INSERT INTO Movie_Languages (movie_id, available_language) VALUES
(1, 'English'), (1, 'Italian'),
(2, 'English'), (2, 'Italian'),
(3, 'Korean'), (3, 'Italian'),
(4, 'French'), (4, 'Italian'),
(5, 'English'), (5, 'Italian'),
(6, 'Japanese'), (6, 'Italian'),
(7, 'English'), (7, 'Italian'),
(8, 'English'), (8, 'Italian'),
(9, 'English'), (9, 'Italian');

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
(2, '2026-11-22', '20:00:00', 'French', 4, 0),
(1, '2026-11-23', '16:00:00', 'English', 9, 2);

-- 10) Ticket Purchases
INSERT INTO Ticket_Purchase (purchase_id, tot_amount, ticket_sold, payment_type, client_id, room_id, screening_date, screening_time, p_method_id) VALUES
(1, 24.00, 2, 'Credit Card', 1, 1, '2026-11-15', '15:30:00', 1),   
(2, 14.40, 1, 'PayPal', 1, 2, '2026-11-15', '18:30:00', 2),   
(3, 12.00, 1, 'Credit Card', 2, 1, '2026-11-15', '15:30:00', 3),   
(4, 32.00, 2, 'Credit Card', 2, 3, '2026-11-15', '19:30:00', 3),   
(5, 36.80, 2, 'Apple Pay', 3, 4, '2026-11-16', '16:00:00', 4),   
(6, 12.00, 1, 'Credit Card', 4, 1, '2026-11-17', '17:00:00', 5),   
(7, 92.00, 5, 'Cash', 6, 4, '2026-11-16', '16:00:00', NULL),
(8, 108.00, 9, 'Google Pay', 5, 99, '2026-11-25', '21:00:00', 6),
(9, 30.00, 2, 'Credit Card', 7, 1, '2026-11-23', '16:00:00', 7);
