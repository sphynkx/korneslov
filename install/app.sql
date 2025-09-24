-- Create DB
CREATE DATABASE IF NOT EXISTS korneslov CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE korneslov;

-- Store books names
CREATE TABLE IF NOT EXISTS books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bookname_ru VARCHAR(64) NOT NULL,
    bookname_en VARCHAR(64) NOT NULL,
    category VARCHAR(64) NOT NULL,
    synonyms_ru TEXT,
    synonyms_en TEXT,
    max_chapter INT NOT NULL,
    max_verses LONGTEXT NOT NULL,
    hits INT NOT NULL DEFAULT 0
);

-- Users' requests
CREATE TABLE IF NOT EXISTS requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    user_state TEXT,
    datetime_request DATETIME,
    datetime_response DATETIME,
    delay FLOAT,
    request TEXT,
    status_oai BOOLEAN,
    status_tg BOOLEAN
);

-- Info about bot's users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    firstname VARCHAR(128),
    lastname VARCHAR(128),
    username VARCHAR(128),
    lang VARCHAR(8) DEFAULT 'ru',
    is_bot BOOLEAN DEFAULT FALSE,
    blacklisted BOOLEAN DEFAULT FALSE,
    whitelisted BOOLEAN DEFAULT FALSE,
    request_id INT,
    last_seen DATETIME,
    amount INT DEFAULT 0,
    external_id VARCHAR(64),
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE SET NULL
);

-- OpenAI responses
CREATE TABLE IF NOT EXISTS responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    data LONGTEXT,
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tribute (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    product_id VARCHAR(128) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    status VARCHAR(16) NOT NULL,
    external_id VARCHAR(64) NOT NULL,
    datetime DATETIME NOT NULL,
    raw_json TEXT,
    UNIQUE KEY (external_id)
);

-- Admin users for admin panel
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(128),
    role VARCHAR(32) DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

