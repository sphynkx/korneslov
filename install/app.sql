-- Create DB
CREATE DATABASE IF NOT EXISTS korneslov CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE korneslov;

-- Store books names
CREATE TABLE IF NOT EXISTS books (
    id INT AUTO_INCREMENT PRIMARY KEY,
	book_id INT NULL,
    bookname_ru VARCHAR(64) NOT NULL,
    bookname_en VARCHAR(64) NOT NULL,
    category VARCHAR(64) NOT NULL,
    synonyms_ru TEXT,
    synonyms_en TEXT,
    max_chapter INT NOT NULL,
    max_verses LONGTEXT NOT NULL,
    hits INT NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX ux_books_book_id ON books(book_id);

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

-- Telegram Bot Payment
CREATE TABLE IF NOT EXISTS tgpayments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    payload VARCHAR(128) NOT NULL,
    amount INT NOT NULL,
    currency VARCHAR(8) NOT NULL,
    status VARCHAR(16) NOT NULL,
    provider_payment_charge_id VARCHAR(128),
    telegram_payment_charge_id VARCHAR(128),
    datetime DATETIME NOT NULL,
    raw_json TEXT,
    UNIQUE KEY uniq_provider_payment_charge_id (provider_payment_charge_id),
    UNIQUE KEY uniq_telegram_payment_charge_id (telegram_payment_charge_id)
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

CREATE TABLE IF NOT EXISTS sources (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(32) NOT NULL UNIQUE,      -- WLC / SYNODAL / KJV
  lang CHAR(2) NOT NULL,                 -- he / ru / en
  title VARCHAR(255) NOT NULL,
  license TEXT,
  notes TEXT,
  canon_group VARCHAR(32) NOT NULL DEFAULT 'protestant_66',
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS verse_texts (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  book_id INT NOT NULL,                  -- stable book_id (1..39 OT; 1000+ extra)
  chapter SMALLINT NOT NULL,
  verse SMALLINT NOT NULL,
  source_id INT NOT NULL,
  text MEDIUMTEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_verse_texts_source FOREIGN KEY (source_id) REFERENCES sources(id),

  UNIQUE KEY ux_verse_texts_addr (book_id, chapter, verse, source_id),
  KEY ix_verse_texts_lookup (source_id, book_id, chapter, verse),
  KEY ix_verse_texts_chapter (source_id, book_id, chapter)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;