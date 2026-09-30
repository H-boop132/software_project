-- ============================================================
-- 微澜 Microripple · 04 为种子微澜关联配图
-- 执行：mysql -u root -p weilan < sql/04_add_images.sql
-- 前置：需先执行 02_schema.sql（含 images 字段）与 03_seed.sql
-- 图片文件位于 backend/uploads/，通过 /uploads 静态访问
-- ============================================================

USE `weilan`;

-- 微澜 #1 编程顿悟（1 张）
UPDATE `ripples` SET `images` = JSON_ARRAY('/uploads/ripple-1-a.jpeg') WHERE `id` = 1;

-- 微澜 #2 图书馆夕阳（1 张）
UPDATE `ripples` SET `images` = JSON_ARRAY('/uploads/ripple-2-a.jpeg') WHERE `id` = 2;

-- 微澜 #3 凌晨老歌（6 张，演示多图横滑）
UPDATE `ripples` SET `images` = JSON_ARRAY(
  '/uploads/ripple-3-a.jpeg',
  '/uploads/ripple-3-b.jpeg',
  '/uploads/ripple-3-c.jpeg',
  '/uploads/ripple-3-d.jpeg',
  '/uploads/ripple-3-e.jpeg',
  '/uploads/ripple-3-f.jpeg'
) WHERE `id` = 3;

-- 微澜 #4 AI 与梦境（1 张）
UPDATE `ripples` SET `images` = JSON_ARRAY('/uploads/ripple-4-a.jpeg') WHERE `id` = 4;

-- 微澜 #5 百年孤独（2 张，演示多图网格）
UPDATE `ripples` SET `images` = JSON_ARRAY('/uploads/ripple-5-a.jpeg', '/uploads/ripple-5-b.jpeg') WHERE `id` = 5;

-- 微澜 #6 调试 bug（1 张）
UPDATE `ripples` SET `images` = JSON_ARRAY('/uploads/ripple-6-a.jpeg') WHERE `id` = 6;
