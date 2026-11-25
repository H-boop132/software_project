-- ============================================================
-- 微澜 Microripple · 11 举报与申诉
-- 执行：mysql -u root -p weilan < sql/11_reports_appeals.sql
-- 说明：新增举报表与申诉表；可重复执行。
-- ============================================================

USE `weilan`;

CREATE TABLE IF NOT EXISTS `reports` (
    `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '举报ID',
    `reporter_id` BIGINT UNSIGNED NOT NULL COMMENT '举报人',
    `ripple_id`   BIGINT UNSIGNED NOT NULL COMMENT '被举报微澜',
    `reason_code` VARCHAR(20)     NOT NULL COMMENT 'spam/abuse/misinformation/illegal/other',
    `detail`      VARCHAR(200)    DEFAULT NULL COMMENT '补充说明',
    `status`      VARCHAR(20)     NOT NULL DEFAULT 'pending' COMMENT 'pending/uphold/dismissed',
    `handler_id`  BIGINT UNSIGNED DEFAULT NULL COMMENT '处理的管理员',
    `handle_note` VARCHAR(200)    DEFAULT NULL COMMENT '处理说明（会通知举报人）',
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `handled_at`  DATETIME        DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_reports_status_time` (`status`, `created_at`),
    KEY `idx_reports_ripple` (`ripple_id`),
    KEY `idx_reports_reporter` (`reporter_id`),
    CONSTRAINT `fk_reports_reporter` FOREIGN KEY (`reporter_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_reports_ripple` FOREIGN KEY (`ripple_id`) REFERENCES `ripples` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_reports_handler` FOREIGN KEY (`handler_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE = InnoDB COMMENT = '微澜举报';

CREATE TABLE IF NOT EXISTS `appeals` (
    `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '申诉ID',
    `user_id`     BIGINT UNSIGNED NOT NULL COMMENT '申诉作者',
    `ripple_id`   BIGINT UNSIGNED NOT NULL COMMENT '申诉微澜',
    `reason`      VARCHAR(200)    NOT NULL COMMENT '申诉理由',
    `status`      VARCHAR(20)     NOT NULL DEFAULT 'pending' COMMENT 'pending/approved/rejected',
    `handler_id`  BIGINT UNSIGNED DEFAULT NULL COMMENT '处理的管理员',
    `handle_note` VARCHAR(200)    DEFAULT NULL COMMENT '处理说明（会通知作者）',
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `handled_at`  DATETIME        DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_appeals_status_time` (`status`, `created_at`),
    KEY `idx_appeals_ripple` (`ripple_id`),
    KEY `idx_appeals_user` (`user_id`),
    CONSTRAINT `fk_appeals_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_appeals_ripple` FOREIGN KEY (`ripple_id`) REFERENCES `ripples` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_appeals_handler` FOREIGN KEY (`handler_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE = InnoDB COMMENT = '微澜申诉';
