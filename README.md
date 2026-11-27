# 微澜 Microripple

> 捕捉每一朵思想涟漪 —— 一个让「一闪而过的念头」被记录、回应、共振的灵感微社交平台。

## 项目定位

「微澜」是一款轻社交灵感平台：用户发布不超过 200 字的灵感碎片（**微澜**），其他用户以
更短的片段回应（**回声**），灵感与回应层层扩散，形成思想波纹。平台通过**话题潮汐榜**与
**情绪气象图**，让零散的念头呈现出集体的节奏与温度。

### 核心概念

| 概念 | 英文 | 说明 |
| --- | --- | --- |
| 微澜 | Ripple | 一条 ≤200 字的灵感/想法碎片，可附加情绪色与话题标签 |
| 回声 | Echo | 对某条微澜的衍生回应，允许继续回应形成涟漪树 |
| 潮汐 | Tide | 话题热度随时间涨落形成的动态榜（区别于静态热度榜） |
| 气象 | Mood Weather | 聚合全站微澜情绪标签，生成实时情绪占比图 |

### 审核与封禁机制（参考抖音处置逻辑）

- **内容封禁**：管理员可封禁违规微澜 → 下架为「仅作者可见」（时间线不再展示）；作者在个人主页能看到自己的违规内容，可**修改后重新提交审核**；内容进入管理员**审核队列**，通过后恢复公开，驳回则保持仅作者可见、可再次修改。
- **账号封禁**：管理员可封禁用户并**指定时长**（1/7/30 天或永久，含原因）；封禁期内无法登录、无法进行任何操作；**到期自动解封**，永久封禁需手动解封。
- **操作留痕**：所有封禁/解封/审核动作写入 `user_bans`、`ripple_reviews` 审计表；举报与申诉记录分别写入 `reports`、`appeals`，申诉处理同时写入审核审计。
- **微澜状态机**：`published`（公开）→ 封禁 → `banned`（仅作者可见）→ 作者修改提交 → `pending`（审核中）→ 通过回到 `published` / 驳回回到 `banned`；作者也可对 `banned` 内容发起申诉，管理员通过后恢复 `published`。
- 发布微澜可附带**最多 9 张配图**（上传后存于 `backend/uploads/`，通过 `/uploads` 静态访问）；修改重提后**发布时间更新为提交审核的时间**。
- 管理员不提供发布微澜功能（入口隐藏 + 后端拦截）；管理端内容列表支持**关键词搜索**与**发布时间范围筛选**（今天/近 7 天/近 30 天/自定义）。

### 我的微澜

登录后点击顶部昵称，进入「我的微澜」。可以按关键词和发布状态筛选，编辑已发布的正文，或查看审核意见并重新提交。删除后内容和回声退出社区展示，数据库保留审核记录。

### 举报与申诉

- **举报**：登录用户可举报他人的已发布微澜，理由分为广告引流、攻击骚扰、不实信息、违法违规、其他，可附 200 字说明；不能举报自己的内容，同一用户对同一条微澜只保留一条待处理举报。
- **举报处理**：管理员在管理后台「举报处理」中查看队列。「成立」会下架微澜并关闭该内容下所有待处理举报，同时通知举报人与作者；「不成立」只关闭当前举报并通知举报人。
- **申诉**：只有被下架微澜的作者可以申诉，同一微澜同时只允许一条待处理申诉；被驳回后可补充理由再次申诉。申诉入口和当前状态会显示在微澜详情页与「我的微澜」。
- **申诉处理**：管理员在「申诉处理」中「通过」后恢复公开并写入 `ripple_reviews` 审计；「驳回」则维持下架。两种结果都会通过站内消息通知作者。
- **消息中心**新增「举报结果」「申诉结果」分类；管理概览同步显示待处理举报、待处理申诉数量。

### 灵感轨迹与处理记录

- 个人中心展示本人公开微澜总数、来自他人的回声和点赞，以及近 30 天的每日公开微澜数量。点击每日柱条可查看日期和数量，统计只对本人开放。
- 从个人中心「举报与申诉记录」或对应结果消息进入处理记录页，查看提交理由、处理状态、时间和管理员反馈，支持按状态筛选与分页。
- 举报记录中的下架或删除内容不展示正文和详情链接。申诉记录允许作者查看自己的下架内容，删除后隐藏原文。
- 同一事项被多位管理员同时处理时，只有一次操作生效。作者删除内容后，管理员仍可关闭待处理事项。

### 汇报演示建议

1. 用普通账号发布一条带话题、情绪和配图的微澜，再从个人中心刷新灵感轨迹，展示新记录。
2. 用另一普通账号点赞、收藏和回复，继续回复一条回声，在涟漪树中展开分支、选择节点。
3. 从话题名进入话题页并订阅，回到首页切换到「订阅的话题」，演示搜索与筛选。
4. 在潮汐榜选择话题，展示互动分变化；在情绪气象选择对应情绪，打开筛选后的内容。
5. 用另一普通账号举报新发布的演示内容，用管理员账号在「举报处理」中处理。回到举报人的处理记录页展示状态与反馈。
6. 作者从下架通知打开原微澜，提交申诉；管理员处理后，作者从申诉结果消息进入处理记录页。申诉通过后展示内容恢复公开。

普通测试账号为 `demo`、`lin`、`ke`、`you`，初始密码 `demo123456`；管理员为 `admin`，初始密码 `admin123456`。建议准备两个浏览器会话，分别用于用户与管理员。种子数据发布时间较早，近 30 天轨迹和近 24 小时互动分可能为零，现场新发布和互动后会按实际数据变化。

### 丰富演示数据

在已完成数据库初始化和增量升级的本地开发环境中，从 `backend` 目录执行：

```powershell
python scripts/seed_demo_community.py
```

脚本在一个事务中补充 6 个普通演示账号、15 条微澜、90 条回声及点赞、收藏、关注、话题订阅记录，可重复运行。主示例「校园灵感交换会」包含四条主分支、28 条回声，最深八层，围绕活动方式、场地、海报与新参与者展开讨论。已有旧版主示例会原位更新正文与回声，保留 ID、回复关系和互动记录。其他话题各有一组较小的讨论树，近期内容分布在近 30 天，供潮汐榜、情绪气象与灵感轨迹演示使用。

其中 8 条演示微澜带有插画配图，复用仓库内的图书馆、书桌、夜晚与技术主题素材；包含单图和双图展示。再次运行会为尚无配图的演示微澜补图，已有配图保持原样。

运行结果会输出主示例的实际地址，ID 由各自数据库分配。首页卡片的「查看回声树」可直接进入树图，默认适应画布展示全部分支。选择第八层节点可高亮完整路径，点击「聚焦所选」以 100% 阅读，或点击「在讨论列表中定位」转到对应回声。折叠第一层分支可演示收起整条回复链，「重置视图」可恢复全部分支与全景。

新增账号为 `demo_chen`、`demo_tang`、`demo_xu`、`demo_wen`、`demo_lu`、`demo_qiao`，初始密码均为 `demo123456`。内容和互动均为人工构造的演示样例，历史回声通知导入为已读。组员拉取代码后执行相同命令，即可在各自本地生成同组演示数据。

### 长讨论导航与图片加载

- 讨论页展示参与人数、主分支数量和最深层级。列表可按主分支最早发起、最新发起或首条回声点赞数排序，分支内保持时间顺序以便理解上下文。
- 支持展开全部、收起回复、跳到最新回声，以及复制单条回声链接。打开带 `#echo-ID` 的链接会展开并定位对应回声，树图中发出的回复会自动成为所选节点。
- 时间线和个人主页使用最长边 640px 的 WebP 缩略图，点击配图仍查看原图。缩略图首次访问时生成缓存，GIF 保留动效，删除原图时同步清理缓存。拉取代码后需重新执行 `pip install -r requirements.txt`，安装新增的 Pillow 依赖。
- 潮汐榜使用时间衰减热度，并比较相邻两个 24 小时的互动分；情绪气象统计全部当前公开微澜的情绪标签，包含历史内容。

交互参考 [Discourse 的讨论导航](https://meta.discourse.org/t/understanding-discourse-for-new-users/96331/1)和 [Reddit 的评论排序](https://support.reddithelp.com/hc/en-us/articles/19695706914196-What-filters-and-sorts-are-available)，结合微澜的树状回声结构实现。

### 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Pinia + Vue Router + Axios + Element Plus
- **后端**：Python 3 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + JWT 认证
- **数据库**：MySQL 8（脚本见 `sql/` 目录）

### 目录结构

```
software_project/
├── README.md              # 项目说明（本文件）
├── docs/                  # 架构与设计文档
├── sql/                   # MySQL 数据库脚本（建库/建表/种子数据）
├── backend/               # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py        # 应用入口：CORS、路由注册、健康检查
│   │   ├── core/          # 配置、数据库会话、安全（JWT/密码哈希）
│   │   ├── api/v1/        # 版本化路由与接口实现
│   │   ├── models/        # SQLAlchemy ORM 模型
│   │   ├── schemas/       # Pydantic 请求/响应模型
│   │   └── services/      # 业务逻辑层
│   ├── requirements.txt
│   ├── .env.example       # 环境变量样例（复制为 .env 后填写）
│   └── run.py             # 开发启动脚本
└── frontend/              # Vue 3 前端
    ├── src/
    │   ├── api/           # Axios 封装与接口定义
    │   ├── router/        # 路由
    │   ├── stores/        # Pinia 状态
    │   ├── views/         # 页面（首页/发布/详情/潮汐/气象/个人）
    │   └── components/    # 通用组件
    └── vite.config.ts
```

## 快速启动

### 0. 前置要求

- Node.js ≥ 18（本机 v22 ✓）
- Python ≥ 3.10（本机 3.14 ✓）
- MySQL 8.x 服务已启动（本机 MySQL80 ✓）

### 1. 初始化数据库

```bash
# Windows（PowerShell / CMD 均可），mysql.exe 路径按本机实际位置调整
cmd /c "mysql -u root -p < sql\01_create_database.sql"
cmd /c "mysql -u root -p weilan < sql\02_schema.sql"
cmd /c "mysql -u root -p weilan < sql\03_seed.sql"
cmd /c "mysql -u root -p weilan < sql\04_add_images.sql"   # 可选：为种子微澜关联示例配图（图片在 backend/uploads/）
```

种子数据内置 5 个账号：**4 个普通用户密码为 `demo123456`，管理员为 `admin123456`**：

| 用户名 | 昵称 | 角色 | 密码 |
| --- | --- | --- | --- |
| `demo` | 微澜观察员 | 普通用户 | demo123456 |
| `lin` | 林小满 | 普通用户 | demo123456 |
| `ke` | 柯北 | 普通用户 | demo123456 |
| `you` | 有容 | 普通用户 | demo123456 |
| `admin` | 微澜管理员 | 管理员 | admin123456 |


已有本地数据库升级时，只执行下面的增量脚本。重新执行 `02_schema.sql` 会重建表。

```bash
cmd /c "mysql -u root -p weilan < sql\05_notifications.sql"
cmd /c "mysql -u root -p weilan < sql\06_topic_subscriptions.sql"
cmd /c "mysql -u root -p weilan < sql\07_moderation_notifications.sql"
cmd /c "mysql -u root -p weilan < sql\08_echo_likes.sql"
cmd /c "mysql -u root -p weilan < sql\09_echo_like_notifications.sql"
cmd /c "mysql -u root -p weilan < sql\10_profile_privacy.sql"
cmd /c "mysql -u root -p weilan < sql\11_reports_appeals.sql"
```

新库直接执行 `02_schema.sql` 即可，其中已包含举报、申诉表；`11_reports_appeals.sql` 用于已有数据库的增量升级。

登录后可从顶部「消息」查看新收到的回声、回复、关注、点赞（微澜/回声）、收藏，以及举报和申诉的处理结果。旧互动不会补发通知。点微澜卡片或潮汐榜上的话题名进入话题页，订阅后可在首页「订阅的话题」查看动态。个人主页的「关注 / 粉丝 / 喜欢 / 收藏」可分别设置为仅自己可见；隐藏后访客打开对应列表会看到「不对外开放」提示。全站轻提示统一显示 1 秒。

### 2. 启动后端（端口 8000）

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # 修改 DATABASE_URL 中的密码为你的 MySQL 密码
python run.py
# 接口文档: http://127.0.0.1:8000/docs
```

### 3. 启动前端（端口 5173）

```bash
cd frontend
npm install
npm run dev
# 访问: http://127.0.0.1:5173
```

## 核心接口

| 模块 | 接口 | 说明 |
| --- | --- | --- |
| 系统 | `GET /api/v1/health` | 健康检查（含数据库连通性） |
| 认证 | `POST /api/v1/auth/register` `POST /api/v1/auth/login` | 注册 / 登录（JWT；封禁账号拒绝登录） |
| 用户 | `GET /api/v1/users/me` `GET /api/v1/users/{id}` | 当前用户 / 用户主页 |
| 用户 | `PUT /api/v1/users/me/privacy` | 设置关注/粉丝/喜欢/收藏列表是否仅自己可见 |
| 用户 | `GET /api/v1/users/{id}/likes` `GET /api/v1/users/{id}/collections` | 用户公开的喜欢 / 收藏列表（隐藏时 403） |
| 微澜 | `GET/POST /api/v1/ripples` `GET /api/v1/ripples/{id}` | 时间线 / 发布 / 详情（封禁内容仅作者可见） |
| 微澜 | `GET /api/v1/ripples/mine` `PUT /api/v1/ripples/{id}` | 我的全部微澜（含封禁/待审核）/ 修改重提审核 |
| 微澜 | `POST /api/v1/ripples/{id}/report` `POST /api/v1/ripples/{id}/appeal` | 举报公开微澜 / 作者申诉已下架微澜 |
| 回声 | `POST /api/v1/ripples/{id}/echoes` `PUT/DELETE /api/v1/echoes/{echo_id}/like` | 发表回声 / 给回声点赞或取消 |
| 互动 | `PUT/DELETE /api/v1/interactions/ripples/{id}/like` `GET /api/v1/interactions/likes` | 点赞 / 取消点赞 / 我的喜欢（分页，按点赞时间倒序） |
| 互动 | `PUT/DELETE /api/v1/interactions/ripples/{id}/collection` `GET /api/v1/interactions/collections` | 收藏 / 取消收藏 / 我的收藏（分页） |
| 搜索 | `GET /api/v1/ripples?keyword=` `&start=` `&end=` | 关键词 + 发布时间范围筛选（首页与管理端共用） |
| 上传 | `POST /api/v1/upload` | 配图上传（jpg/png/webp/gif，≤5MB，需登录）；发布微澜最多带 9 张 |
| 潮汐 | `GET /api/v1/tides/hot` | 话题潮汐榜（热度 + 涨落） |
| 气象 | `GET /api/v1/moods/summary` | 全站情绪气象聚合 |
| 管理 | `GET /api/v1/admin/stats` `GET /admin/users` `GET /admin/ripples` | 平台统计 / 用户列表 / 全部内容（仅管理员） |
| 管理 | `POST /admin/users/{id}/ban` `POST /admin/users/{id}/unban` | 封禁用户（指定时长）/ 解封 |
| 管理 | `POST /admin/ripples/{id}/ban` `GET /admin/reviews` | 封禁微澜 / 待审核队列 |
| 管理 | `POST /admin/ripples/{id}/approve` `POST /admin/ripples/{id}/reject` `DELETE /admin/ripples/{id}` | 审核通过 / 驳回 / 删除 |
| 管理 | `GET /admin/reports` `POST /admin/reports/{id}/handle` | 举报队列 / 处理举报（成立下架或关闭） |
| 管理 | `GET /admin/appeals` `POST /admin/appeals/{id}/handle` | 申诉队列 / 处理申诉（恢复公开或维持下架） |

## Roadmap（后续版本）

当前稳定版本分支：`main`。包含公开用户主页、关注与粉丝列表、关注时间线、回声讨论和可缩放树图；后端接口文档版本为 `0.2.0`。

- **开发进展**：已完成点赞 / 取消点赞、收藏 / 取消收藏、个人中心的「我的喜欢」和「我的收藏」、主页列表可见范围、举报与申诉闭环。[点赞验收记录](docs/点赞阶段验收记录.md)、[收藏验收记录](docs/收藏阶段验收记录.md)和[我的收藏验收记录](docs/我的收藏阶段验收记录.md)包含接口、测试命令与演示截图。

- **v0.1（已完成）**：框架骨架 + 审核封禁体系 —— 数据库脚本、后端分层与认证、登录拦截、管理后台（统计/审核队列/用户封禁/内容封禁）、我的微澜与修改重提
- **v0.2（当前，已完成）**：点赞 / 收藏 / 关注关系闭环，回声发表与回复、涟漪树可视化，以及潮汐时间衰减。见 [v0.2 完整验收记录](docs/v0.2完整验收记录.md)。
- **v0.3**：个人灵感轨迹图、话题订阅与推送
- **v0.4**：AI 共振 —— 基于语义为新微澜匹配历史相关微澜（预留接口）
- **v0.5**：情绪气象实时大屏、消息推送
