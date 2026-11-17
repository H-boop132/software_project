-- 已有数据库增量升级，可重复运行。
CREATE TABLE IF NOT EXISTS `topic_subscriptions` (
    `user_id` BIGINT UNSIGNED NOT NULL,
    `topic_id` BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (`user_id`, `topic_id`),
    KEY `idx_topic_subscriptions_topic` (`topic_id`),
    CONSTRAINT `fk_topic_subscriptions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_topic_subscriptions_topic` FOREIGN KEY (`topic_id`) REFERENCES `topics` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
