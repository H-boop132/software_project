-- ============================================================
-- 微澜 Microripple · 02 建表（MySQL 8.x）
-- 执行：mysql -u root -p weilan < sql/02_schema.sql
-- 说明：utf8mb4 字符集；InnoDB；外键 ON DELETE CASCADE 级联清理
-- 可重复执行：先按「子表→父表」顺序删除全部旧表，再统一重建
-- ============================================================

USE `weilan`;

-- ------------------------------------------------------------
-- 统一清理旧表（子表在前、父表在后，避免外键引用导致 DROP 失败）
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `user_bans`;
DROP TABLE IF EXISTS `ripple_reviews`;
DROP TABLE IF EXISTS `echoes`;
DROP TABLE IF EXISTS `likes`;
DROP TABLE IF EXISTS `follows`;
DROP TABLE IF EXISTS `collections`;
DROP TABLE IF EXISTS `ripples`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `topics`;
DROP TABLE IF EXISTS `emotions`;

-- ------------------------------------------------------------
-- 用户表
-- ------------------------------------------------------------
CREATE TABLE `users` (
    `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    `username`      VARCHAR(50)     NOT NULL COMMENT '登录名（唯一）',
    `nickname`      VARCHAR(50)     NOT NULL COMMENT '昵称',
    `password_hash` VARCHAR(255)    NOT NULL COMMENT 'PBKDF2-SHA256 哈希（pbkdf2_sha256$迭代$盐$摘要）',
    `avatar_url`    VARCHAR(255)    DEFAULT NULL COMMENT '头像地址',
    `bio`           VARCHAR(200)    DEFAULT NULL COMMENT '个人签名',
    `mood_tone`     VARCHAR(20)     DEFAULT NULL COMMENT '情绪色调偏好（emotions.code）',
    `role`          VARCHAR(20)     NOT NULL DEFAULT 'user' COMMENT '角色：user 普通用户 / admin 管理员',
    `ban_status`    VARCHAR(20)     NOT NULL DEFAULT 'active' COMMENT '封禁状态：active 正常 / banned 封禁中',
    `ban_until`     DATETIME        DEFAULT NULL COMMENT '封禁截止时间，NULL=永久封禁',
    `ban_reason`    VARCHAR(200)    DEFAULT NULL COMMENT '封禁原因',
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`)
) ENGINE = InnoDB COMMENT = '用户';

-- ------------------------------------------------------------
-- 话题表
-- ------------------------------------------------------------
CREATE TABLE `topics` (
    `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '话题ID',
    `name`        VARCHAR(50)     NOT NULL COMMENT '话题名（如 深夜电台）',
    `slug`        VARCHAR(50)     NOT NULL COMMENT '唯一标识（url 用）',
    `description` VARCHAR(200)    DEFAULT NULL COMMENT '话题简介',
    `heat_base`   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '热度基数（潮汐计算用）',
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_slug` (`slug`)
) ENGINE = InnoDB COMMENT = '话题';

-- ------------------------------------------------------------
-- 情绪字典表（微澜可附加的情绪色）
-- ------------------------------------------------------------
CREATE TABLE `emotions` (
    `code` VARCHAR(20)  NOT NULL COMMENT '情绪编码（joy/anger/...）',
    `name` VARCHAR(20)  NOT NULL COMMENT '中文名（喜悦）',
    `color` CHAR(7)     NOT NULL COMMENT '代表色 #RRGGBB',
    PRIMARY KEY (`code`)
) ENGINE = InnoDB COMMENT = '情绪字典';

-- ------------------------------------------------------------
-- 微澜表（灵感碎片，根节点，≤200字）
-- ------------------------------------------------------------
CREATE TABLE `ripples` (
    `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '微澜ID',
    `user_id`      BIGINT UNSIGNED NOT NULL COMMENT '发布者',
    `content`      VARCHAR(200)    NOT NULL COMMENT '灵感正文（≤200字）',
    `topic_id`     BIGINT UNSIGNED DEFAULT NULL COMMENT '所属话题',
    `emotion_code` VARCHAR(20)     DEFAULT NULL COMMENT '情绪色（emotions.code）',
    `status`       VARCHAR(20)     NOT NULL DEFAULT 'published' COMMENT '状态：published 已发布 / banned 已封禁（仅作者可见）/ pending 修改后待审核',
    `images`       JSON            DEFAULT NULL COMMENT '配图 URL 数组，最多 9 张',
    `created_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
    `updated_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_created` (`user_id`, `created_at`),
    KEY `idx_topic_created` (`topic_id`, `created_at`),
    CONSTRAINT `fk_ripples_user`   FOREIGN KEY (`user_id`)      REFERENCES `users` (`id`)   ON DELETE CASCADE,
    CONSTRAINT `fk_ripples_topic`  FOREIGN KEY (`topic_id`)     REFERENCES `topics` (`id`)  ON DELETE SET NULL,
    CONSTRAINT `fk_ripples_emotion` FOREIGN KEY (`emotion_code`) REFERENCES `emotions` (`code`) ON DELETE SET NULL
) ENGINE = InnoDB COMMENT = '微澜（灵感碎片）';

-- ------------------------------------------------------------
-- 回声表（对微澜的回应，形成涟漪树）
-- root_ripple_id：所在树的根微澜（整树查询用）
-- parent_echo_id：NULL 表示直接回应根微澜
-- ------------------------------------------------------------
CREATE TABLE `echoes` (
    `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '回声ID',
    `root_ripple_id` BIGINT UNSIGNED NOT NULL COMMENT '涟漪树根（微澜ID）',
    `parent_echo_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '父回声（NULL=直接回应根微澜）',
    `user_id`        BIGINT UNSIGNED NOT NULL COMMENT '回应者',
    `content`        VARCHAR(200)    NOT NULL COMMENT '回应内容（≤200字）',
    `emotion_code`   VARCHAR(20)     DEFAULT NULL COMMENT '情绪色',
    `created_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '回应时间',
    PRIMARY KEY (`id`),
    KEY `idx_root_created` (`root_ripple_id`, `created_at`),
    KEY `idx_parent` (`parent_echo_id`),
    CONSTRAINT `fk_echoes_root`  FOREIGN KEY (`root_ripple_id`) REFERENCES `ripples` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_echoes_parent` FOREIGN KEY (`parent_echo_id`) REFERENCES `echoes` (`id`)  ON DELETE CASCADE,
    CONSTRAINT `fk_echoes_user`  FOREIGN KEY (`user_id`)        REFERENCES `users` (`id`)   ON DELETE CASCADE,
    CONSTRAINT `fk_echoes_emotion` FOREIGN KEY (`emotion_code`) REFERENCES `emotions` (`code`) ON DELETE SET NULL
) ENGINE = InnoDB COMMENT = '回声（回应）';

-- ------------------------------------------------------------
-- 点赞表（对微澜）
-- ------------------------------------------------------------
CREATE TABLE `likes` (
    `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '点赞ID',
    `user_id`    BIGINT UNSIGNED NOT NULL COMMENT '点赞者',
    `ripple_id`  BIGINT UNSIGNED NOT NULL COMMENT '被点赞微澜',
    `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_ripple` (`user_id`, `ripple_id`),
    KEY `idx_ripple` (`ripple_id`),
    CONSTRAINT `fk_likes_user`   FOREIGN KEY (`user_id`)   REFERENCES `users` (`id`)  ON DELETE CASCADE,
    CONSTRAINT `fk_likes_ripple` FOREIGN KEY (`ripple_id`) REFERENCES `ripples` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '点赞';

-- ------------------------------------------------------------
-- 关注表
-- ------------------------------------------------------------
CREATE TABLE `follows` (
    `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '关注ID',
    `follower_id` BIGINT UNSIGNED NOT NULL COMMENT '关注者',
    `followee_id` BIGINT UNSIGNED NOT NULL COMMENT '被关注者',
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '关注时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_follow` (`follower_id`, `followee_id`),
    KEY `idx_followee` (`followee_id`),
    CONSTRAINT `fk_follows_follower` FOREIGN KEY (`follower_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_follows_followee` FOREIGN KEY (`followee_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '关注';

-- ------------------------------------------------------------
-- 收藏表
-- ------------------------------------------------------------
CREATE TABLE `collections` (
    `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '收藏ID',
    `user_id`    BIGINT UNSIGNED NOT NULL COMMENT '收藏者',
    `ripple_id`  BIGINT UNSIGNED NOT NULL COMMENT '被收藏微澜',
    `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_ripple` (`user_id`, `ripple_id`),
    KEY `idx_ripple` (`ripple_id`),
    CONSTRAINT `fk_collections_user`   FOREIGN KEY (`user_id`)   REFERENCES `users` (`id`)  ON DELETE CASCADE,
    CONSTRAINT `fk_collections_ripple` FOREIGN KEY (`ripple_id`) REFERENCES `ripples` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '收藏';

-- ------------------------------------------------------------
-- 用户封禁审计表（管理员操作留痕）
-- duration_days：封禁天数；NULL = 永久封禁
-- ban_until：到期时间；NULL = 永久
-- ------------------------------------------------------------
CREATE TABLE `user_bans` (
    `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    `user_id`       BIGINT UNSIGNED NOT NULL COMMENT '被封禁用户',
    `admin_id`      BIGINT UNSIGNED NOT NULL COMMENT '操作管理员',
    `duration_days` INT UNSIGNED    DEFAULT NULL COMMENT '封禁天数，NULL=永久',
    `reason`        VARCHAR(200)    DEFAULT NULL COMMENT '封禁原因',
    `ban_until`     DATETIME        DEFAULT NULL COMMENT '到期时间，NULL=永久',
    `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    PRIMARY KEY (`id`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_userbans_user`  FOREIGN KEY (`user_id`)  REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_userbans_admin` FOREIGN KEY (`admin_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '用户封禁审计';

-- ------------------------------------------------------------
-- 微澜审核审计表（封禁/通过/驳回留痕）
-- action：ban 封禁 / approve 审核通过 / reject 审核驳回
-- ------------------------------------------------------------
CREATE TABLE `ripple_reviews` (
    `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    `ripple_id`   BIGINT UNSIGNED NOT NULL COMMENT '被审核微澜',
    `reviewer_id` BIGINT UNSIGNED NOT NULL COMMENT '审核管理员',
    `action`      VARCHAR(20)     NOT NULL COMMENT '动作：ban/approve/reject',
    `reason`      VARCHAR(200)    DEFAULT NULL COMMENT '原因',
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    PRIMARY KEY (`id`),
    KEY `idx_ripple` (`ripple_id`),
    CONSTRAINT `fk_reviews_ripple`   FOREIGN KEY (`ripple_id`)   REFERENCES `ripples` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_reviews_reviewer` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`)  ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '微澜审核审计';
