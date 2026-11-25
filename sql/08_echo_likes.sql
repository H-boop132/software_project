-- ============================================================
-- 微澜 Microripple · 08 回声点赞与互动通知
-- 执行：mysql -u root -p weilan < sql/08_echo_likes.sql
-- 说明：可重复执行；只加表/索引，不改动已有数据
-- ============================================================

USE `weilan`;

-- 回复（回声）点赞：与微澜点赞分表，避免 id 语义混淆
CREATE TABLE IF NOT EXISTS `echo_likes` (
    `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '回声点赞ID',
    `user_id`    BIGINT UNSIGNED NOT NULL COMMENT '点赞者',
    `echo_id`    BIGINT UNSIGNED NOT NULL COMMENT '被点赞回声',
    `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_echo` (`user_id`, `echo_id`),
    KEY `idx_echo` (`echo_id`),
    CONSTRAINT `fk_echo_likes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)   ON DELETE CASCADE,
    CONSTRAINT `fk_echo_likes_echo` FOREIGN KEY (`echo_id`) REFERENCES `echoes` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '回声点赞';

-- 点赞/收藏通知按「操作人 + 类型 + 微澜」去重，补一个联合索引
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'notifications'
      AND INDEX_NAME = 'idx_notifications_actor_kind_ripple'
);
SET @sql := IF(
    @idx_exists = 0,
    'ALTER TABLE `notifications` ADD KEY `idx_notifications_actor_kind_ripple` (`actor_id`, `kind`, `ripple_id`)',
    'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
