-- ============================================================
-- 微澜 Microripple · 10 主页列表隐私开关
-- 执行：mysql -u root -p weilan < sql/10_profile_privacy.sql
-- 说明：为个人主页的关注/粉丝/喜欢/收藏列表增加「仅自己可见」开关。
--       默认 0（公开）；可重复执行。
-- ============================================================

USE `weilan`;

SET @exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'hide_following'
);
SET @sql := IF(
    @exists = 0,
    'ALTER TABLE `users` ADD COLUMN `hide_following` TINYINT(1) NOT NULL DEFAULT 0 COMMENT ''隐藏关注列表''',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'hide_followers'
);
SET @sql := IF(
    @exists = 0,
    'ALTER TABLE `users` ADD COLUMN `hide_followers` TINYINT(1) NOT NULL DEFAULT 0 COMMENT ''隐藏粉丝列表''',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'hide_likes'
);
SET @sql := IF(
    @exists = 0,
    'ALTER TABLE `users` ADD COLUMN `hide_likes` TINYINT(1) NOT NULL DEFAULT 0 COMMENT ''隐藏我的喜欢''',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'hide_collections'
);
SET @sql := IF(
    @exists = 0,
    'ALTER TABLE `users` ADD COLUMN `hide_collections` TINYINT(1) NOT NULL DEFAULT 0 COMMENT ''隐藏我的收藏''',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
