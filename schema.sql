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
