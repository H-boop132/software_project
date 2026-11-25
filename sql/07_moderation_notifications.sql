-- 为通知表补充"内容处理"类消息：关联微澜 + 处理说明。
-- 可安全重复执行；已存在的列/索引/外键会被跳过。
-- mysql --default-character-set=utf8mb4 -u root -p weilan < sql/07_moderation_notifications.sql

-- ripple_id
SET @has_col := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notifications' AND COLUMN_NAME = 'ripple_id'
);
SET @ddl := IF(@has_col = 0,
    'ALTER TABLE `notifications` ADD COLUMN `ripple_id` BIGINT UNSIGNED NULL COMMENT ''关联微澜（内容处理通知）'' AFTER `follow_id`',
    'DO 0');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- note
SET @has_col := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notifications' AND COLUMN_NAME = 'note'
);
SET @ddl := IF(@has_col = 0,
    'ALTER TABLE `notifications` ADD COLUMN `note` VARCHAR(200) NULL COMMENT ''处理说明（封禁/驳回原因等）'' AFTER `ripple_id`',
    'DO 0');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 索引
SET @has_idx := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notifications' AND INDEX_NAME = 'idx_notifications_ripple'
);
SET @ddl := IF(@has_idx = 0,
    'ALTER TABLE `notifications` ADD KEY `idx_notifications_ripple` (`ripple_id`)',
    'DO 0');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 外键：微澜删除时通知保留，仅把关联置空（ON DELETE SET NULL）
SET @has_fk := (
    SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notifications'
      AND CONSTRAINT_NAME = 'fk_notifications_ripple'
);
SET @ddl := IF(@has_fk = 0,
    'ALTER TABLE `notifications` ADD CONSTRAINT `fk_notifications_ripple` FOREIGN KEY (`ripple_id`) REFERENCES `ripples` (`id`) ON DELETE SET NULL',
    'DO 0');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
