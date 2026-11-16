-- =====================================================
-- PROJECT: E-commerce Revenue & Customer Retention Intelligence
-- PHASE 5: MySQL Database Setup
-- =====================================================
-- Create a dedicated project database
CREATE DATABASE IF NOT EXISTS ecommerce_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
-- Select the database
USE ecommerce_analytics;
-- Confirm the active database
SELECT DATABASE() AS active_database;
-- Display database details
SELECT SCHEMA_NAME AS database_name,
    DEFAULT_CHARACTER_SET_NAME AS character_set_name,
    DEFAULT_COLLATION_NAME AS collation_name
FROM INFORMATION_SCHEMA.SCHEMATA
WHERE SCHEMA_NAME = 'ecommerce_analytics';