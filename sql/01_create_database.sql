-- ============================================================
-- 微澜 Microripple · 01 创建数据库
-- 执行：mysql -u root -p < sql/01_create_database.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS `weilan`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `weilan`;

-- 统一表字符集：utf8mb4（支持中文与 emoji）
SET NAMES utf8mb4;
