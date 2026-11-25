-- 在已有数据库中执行一次，可安全重复运行。
-- mysql --default-character-set=utf8mb4 -u root -p weilan < sql/05_notifications.sql

CREATE TABLE IF NOT EXISTS `notifications` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `recipient_id` BIGINT UNSIGNED NOT NULL,
    `actor_id` BIGINT UNSIGNED NOT NULL,
    `kind` VARCHAR(12) NOT NULL,
    `echo_id` BIGINT UNSIGNED NULL,
    `follow_id` BIGINT UNSIGNED NULL,
    `ripple_id` BIGINT UNSIGNED NULL COMMENT '关联微澜（内容处理通知）',
    `note` VARCHAR(200) NULL COMMENT '处理说明（封禁/驳回原因等）',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `read_at` DATETIME NULL,
    PRIMARY KEY (`id`),
    KEY `idx_notifications_recipient_id` (`recipient_id`, `id`),
    KEY `idx_notifications_recipient_read` (`recipient_id`, `read_at`),
    KEY `idx_notifications_ripple` (`ripple_id`),
    UNIQUE KEY `uk_notification_echo` (`echo_id`),
    UNIQUE KEY `uk_notification_follow` (`follow_id`),
    CONSTRAINT `fk_notifications_recipient` FOREIGN KEY (`recipient_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_notifications_actor` FOREIGN KEY (`actor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_notifications_echo` FOREIGN KEY (`echo_id`) REFERENCES `echoes` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_notifications_follow` FOREIGN KEY (`follow_id`) REFERENCES `follows` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_notifications_ripple` FOREIGN KEY (`ripple_id`) REFERENCES `ripples` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
