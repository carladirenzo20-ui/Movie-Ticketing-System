-- Part 2: run once against an empty cinema_db. Existing data is never dropped.
CREATE DATABASE IF NOT EXISTS cinema_db;
USE cinema_db;

-- 1) Users
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    address VARCHAR(100),
    name VARCHAR(100) NOT NULL,
    account_role ENUM('client', 'admin') NOT NULL,
    UNIQUE (user_id, account_role),
    CHECK (account_role IN ('client', 'admin')),
    CHECK (account_role <> 'client' OR REGEXP_LIKE(address, '[^[:space:]]') IS TRUE)
) ENGINE=InnoDB;

-- 2) Client (ISA from Users)
CREATE TABLE Client (
    user_id INT PRIMARY KEY,
    account_role ENUM('client', 'admin') GENERATED ALWAYS AS ('client') STORED,
    FOREIGN KEY (user_id, account_role) REFERENCES Users(user_id, account_role)
) ENGINE=InnoDB;

-- 3) Administrator (ISA from Users)
CREATE TABLE Administrator (
    user_id INT PRIMARY KEY,
    account_role ENUM('client', 'admin') GENERATED ALWAYS AS ('admin') STORED,
    FOREIGN KEY (user_id, account_role) REFERENCES Users(user_id, account_role)
) ENGINE=InnoDB;

-- 4) Payment methods; the composite key validates owner and type on purchases
CREATE TABLE Payment_Method (
    p_method_id INT NOT NULL AUTO_INCREMENT,
    client_id INT NOT NULL,
    payment_type VARCHAR(50) NOT NULL,
    card_number VARCHAR(50) NOT NULL,
    billing_address VARCHAR(100),
    expiring_date DATE NOT NULL,
    PRIMARY KEY (p_method_id),
    UNIQUE (p_method_id, client_id, payment_type),
    FOREIGN KEY (client_id) REFERENCES Client(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 5) Theaters
CREATE TABLE Theaters (
    room_id INT PRIMARY KEY,
    max_capacity INT NOT NULL,
    is_3D BOOLEAN NOT NULL DEFAULT FALSE,
    premium_sound BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (max_capacity > 0),
    CHECK (is_3D IN (0, 1)),
    CHECK (premium_sound IN (0, 1))
) ENGINE=InnoDB;

-- 6) Movies
CREATE TABLE Movies (
    movie_id INT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    release_date DATE NOT NULL,
    running_time INT NOT NULL,
    description TEXT NOT NULL,
    original_language VARCHAR(100) NOT NULL,
    primary_genre VARCHAR(100) NOT NULL,
    CHECK (running_time > 0),
    CHECK (REGEXP_LIKE(description, '[^[:space:]]')),
    CHECK (REGEXP_LIKE(primary_genre, '[^[:space:]]'))
) ENGINE=InnoDB;

-- 7) Each movie has a required primary genre and can have additional genres.
CREATE TABLE Movie_Additional_Genres (
    movie_id INT NOT NULL,
    genre VARCHAR(100) NOT NULL,
    PRIMARY KEY (movie_id, genre),
    FOREIGN KEY (movie_id) REFERENCES Movies(movie_id) ON DELETE CASCADE,
    CHECK (REGEXP_LIKE(genre, '[^[:space:]]'))
) ENGINE=InnoDB;

CREATE VIEW Movie_Genres AS
SELECT movie_id, primary_genre AS genre FROM Movies
UNION
SELECT movie_id, genre FROM Movie_Additional_Genres;

-- 8) Movie Available Languages
CREATE TABLE Movie_Languages (
    movie_id INT NOT NULL,
    available_language VARCHAR(100) NOT NULL,
    PRIMARY KEY (movie_id, available_language),
    FOREIGN KEY (movie_id) REFERENCES Movies(movie_id) ON DELETE CASCADE
) ENGINE=InnoDB;

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
) ENGINE=InnoDB;

-- 10) Purchases; referenced payment methods cannot be deleted
CREATE TABLE Ticket_Purchase (
    purchase_id INT AUTO_INCREMENT PRIMARY KEY,
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
    FOREIGN KEY (p_method_id, client_id, payment_type)
        REFERENCES Payment_Method(p_method_id, client_id, payment_type),

    CHECK (ticket_sold > 0),
    CHECK (tot_amount >= 0),
    CHECK (p_method_id IS NOT NULL OR payment_type = 'Cash')
) ENGINE=InnoDB;

-- Useful indexes
CREATE INDEX idx_movies_title ON Movies(title);
CREATE INDEX idx_schedule_datetime ON Schedule(screening_date, screening_time);

DELIMITER $$

CREATE PROCEDURE validate_screening(
    IN target_room INT, IN target_date DATE, IN target_time TIME,
    IN target_movie INT, IN target_language VARCHAR(100), IN sold INT,
    IN check_schedule BOOLEAN, IN old_room INT, IN old_date DATE, IN old_time TIME
)
BEGIN
    DECLARE capacity INT DEFAULT NULL;
    DECLARE duration_minutes INT DEFAULT NULL;
    DECLARE start_second, end_second INT;

    IF check_schedule THEN
        SELECT m.running_time INTO duration_minutes
        FROM Movies m
        JOIN Movie_Languages ml ON ml.movie_id = m.movie_id
        WHERE m.movie_id = target_movie AND ml.available_language = target_language
        FOR SHARE;
        IF duration_minutes IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Unknown movie or language unavailable for the movie.';
        END IF;

        SET start_second = TIME_TO_SEC(target_time);
        IF start_second < TIME_TO_SEC('10:00:00')
            OR duration_minutes * 60 > TIME_TO_SEC('23:59:00') - start_second THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'The screening must fit within 10:00-23:59.';
        END IF;
        SET end_second = start_second + duration_minutes * 60;
    END IF;

    -- Serialize changes in this room, even under READ COMMITTED.
    SELECT max_capacity INTO capacity FROM Theaters WHERE room_id = target_room FOR UPDATE;
    IF capacity IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Unknown theater.';
    END IF;
    IF sold > capacity THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tickets sold cannot exceed theater capacity.';
    END IF;

    -- Read the latest committed schedule after acquiring the room lock.
    IF check_schedule AND EXISTS (
        SELECT 1 FROM Schedule s
        JOIN Movies m ON m.movie_id = s.movie_id
        WHERE s.room_id = target_room AND s.screening_date = target_date
          AND NOT (s.room_id <=> old_room AND s.screening_date <=> old_date AND s.screening_time <=> old_time)
          AND TIME_TO_SEC(s.screening_time) < end_second
          AND TIME_TO_SEC(s.screening_time) + m.running_time * 60 > start_second
        FOR SHARE
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'The theater already has an overlapping screening.';
    END IF;
END$$

CREATE TRIGGER check_new_screening BEFORE INSERT ON Schedule FOR EACH ROW
    CALL validate_screening(NEW.room_id, NEW.screening_date, NEW.screening_time,
                            NEW.movie_id, NEW.movie_language, NEW.tickets_sold,
                            TRUE, NULL, NULL, NULL)$$

CREATE TRIGGER check_updated_screening BEFORE UPDATE ON Schedule FOR EACH ROW
    CALL validate_screening(NEW.room_id, NEW.screening_date, NEW.screening_time,
                            NEW.movie_id, NEW.movie_language, NEW.tickets_sold,
                            NEW.room_id <> OLD.room_id OR NEW.screening_date <> OLD.screening_date
                                OR NEW.screening_time <> OLD.screening_time OR NEW.movie_id <> OLD.movie_id
                                OR NEW.movie_language <> OLD.movie_language,
                            OLD.room_id, OLD.screening_date, OLD.screening_time)$$

CREATE TRIGGER check_reduced_capacity BEFORE UPDATE ON Theaters FOR EACH ROW
BEGIN
    IF NEW.max_capacity < OLD.max_capacity AND EXISTS (
        SELECT 1 FROM Schedule WHERE room_id = OLD.room_id AND tickets_sold > NEW.max_capacity
        FOR SHARE
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'The new capacity is less than the tickets already sold.';
    END IF;
END$$

CREATE TRIGGER check_longer_runtime BEFORE UPDATE ON Movies FOR EACH ROW
BEGIN
    DECLARE room_locks CURSOR FOR SELECT room_id FROM Theaters ORDER BY room_id FOR UPDATE;

    IF NEW.running_time > OLD.running_time THEN
        -- Opening the cursor locks the theater rows until the transaction ends.
        OPEN room_locks;
        CLOSE room_locks;

        IF EXISTS (
            SELECT 1 FROM Schedule s
            WHERE s.movie_id = OLD.movie_id
              AND TIME_TO_SEC(s.screening_time) + NEW.running_time * 60 > TIME_TO_SEC('23:59:00')
            FOR SHARE
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'The new runtime would exceed the cinema closing time.';
        END IF;

        IF EXISTS (
            SELECT 1 FROM Schedule s
            JOIN Schedule next_screening ON next_screening.room_id = s.room_id
                 AND next_screening.screening_date = s.screening_date
                 AND next_screening.screening_time > s.screening_time
            WHERE s.movie_id = OLD.movie_id
              AND TIME_TO_SEC(next_screening.screening_time)
                    < TIME_TO_SEC(s.screening_time) + NEW.running_time * 60
            FOR SHARE
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'The new runtime would make screenings overlap.';
        END IF;
    END IF;
END$$

DELIMITER ;
