CREATE DATABASE IF NOT EXISTS sentimenken_db;
USE sentimenken_db;

CREATE TABLE IF NOT EXISTS news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    input_date DATETIME,
    url VARCHAR(255) NOT NULL,
    publish_date DATE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    compount FLOAT,
    sentiment VARCHAR(50),
);

CREATE TABLE IF NOT EXISTS yields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    yield_date DATE NOT NULL,
    yield_value DECIMAL NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);