-- ============================================================
-- 微澜 Microripple · 09 回声点赞通知
-- 执行：mysql -u root -p weilan < sql/09_echo_like_notifications.sql
-- 说明：把「一条回声只能有一条通知」改为「同一操作人对同一条回声只留一条」，
--       使不同用户点赞同一条回声时，作者都能收到通知。可重复执行。
-- ============================================================

USE `weilan`;

-- 先补一个普通 echo_id 索引，供外键使用，否则旧唯一索引无法删除
SET @fk_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND INDEX_NAME = 'idx_notifications_echo'
);
SET @sql := IF(
    @fk_exists = 0,
    'ALTER TABLE `notifications` ADD KEY `idx_notifications_echo` (`echo_id`)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 删除旧的 echo_id 单列唯一约束
SET @old_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND INDEX_NAME = 'uk_notification_echo'
);
SET @sql := IF(
    @old_exists > 0,
    'ALTER TABLE `notifications` DROP INDEX `uk_notification_echo`',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 新增「接收人 + 操作人 + 类型 + 回声」联合唯一约束
SET @new_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND INDEX_NAME = 'uk_notification_echo_actor'
);
SET @sql := IF(
    @new_exists = 0,
    'ALTER TABLE `notifications` ADD UNIQUE KEY `uk_notification_echo_actor` (`recipient_id`, `actor_id`, `kind`, `echo_id`)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
