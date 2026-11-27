"""Add repeatable local demonstration content without resetting existing data.

Run from backend: python scripts/seed_demo_community.py
The six demo_* accounts created here use the demonstration password demo123456.
"""
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    Collection, Echo, EchoLike, Emotion, Follow, Like, Notification,
    Ripple, Topic, TopicSubscription, User,
)
from app.services.echo_service import MAX_ECHO_DEPTH

LOCK_NAME = "weilan_demo_community_v1"
LEGACY_MAIN_CONTENT = "汇报前的灵感共创：如果只能用五分钟介绍我们的微澜，你最想展示哪个瞬间？我想从一个念头出发，看看它怎样被不同的人接住，最后长成一棵回声树。"
MAIN_CONTENT = "想在校园里办一个周末灵感交换会：每个人带一个最近没想明白的问题，找几位同学一起聊。时间、地点和参与方式怎么安排，才能让第一次来的人也愿意开口？"

NEW_USERS = [
    ("demo_chen", "陈序", "把复杂问题拆成能验证的小步骤。", "think"),
    ("demo_tang", "唐梨", "收集校园里值得记住的小事。", "joy"),
    ("demo_xu", "许知夏", "阅读、散步，也偶尔担心明天。", "calm"),
    ("demo_wen", "闻舟", "听歌的时候，灵感比平时多一点。", "sorrow"),
    ("demo_lu", "陆一帆", "对未来的技术保持好奇。", "fear"),
    ("demo_qiao", "乔安", "希望每一次讨论都能被认真回应。", "anger"),
]

# Keys explicitly identify parents, keeping branches reproducible on repeated runs.
LEGACY_MAIN_TREE = [
    ("a1", None, "lin", "我想展示一个普通想法变成具体方案的过程，先从发布一条微澜开始。", "think"),
    ("a2", "a1", "demo_chen", "然后让另一位同学补充一个不同角度，观众就知道回声不只是评论。", "think"),
    ("a3", "a2", "ke", "比如我会追问：如果这个方案失败了，我们怎样知道是哪一步出了问题？", "fear"),
    ("a4", "a3", "demo", "可以把每一次追问保留成回复关系，回到原来的分支继续讨论。", "think"),
    ("a5", "a4", "demo_lu", "这让我想到调试：先提出猜测，再用一个最小例子验证。", "think"),
    ("a6", "a5", "lin", "验证以后，把结论回复到那条猜测下面，后来的人就能顺着读下来。", "calm"),
    ("a7", "a6", "demo_chen", "还可以保留没被采用的方向，解释我们为什么最后选了这个方案。", "think"),
    ("a8", "a7", "you", "这样一条八层讨论链，就把提问、验证和结论完整留住了。", "joy"),
    ("a3b", "a2", "demo_tang", "我更关心第一次来的同学能否看懂，最好先给一个生活里的例子。", "joy"),
    ("a4b", "a3b", "demo", "例如“图书馆哪里适合小组讨论”，每个人都能补充亲身经验。", "calm"),
    ("b1", None, "demo_qiao", "我想展示不同意见也能好好聊，不用把每次分歧都变成争论。", "think"),
    ("b2", "b1", "ke", "那我们可以在同一个问题下放两个方向，让观众看到分支。", "think"),
    ("b3", "b2", "demo_xu", "一边讨论效率，一边讨论体验，最后再看看有没有折中方案。", "calm"),
    ("b4", "b3", "demo", "这条线先保留“效率”视角，另一条线由关心体验的人继续补充。", "think"),
    ("b2b", "b1", "demo_wen", "我会先讲自己的经历，而不是马上给对方的想法下判断。", "calm"),
    ("b3b", "b2b", "demo_qiao", "对，能接住对方的问题，才有继续回复的可能。", "joy"),
    ("b4b", "b3b", "you", "演示时选中这一条，看看它到原帖的整条路径能否一眼看清。", "think"),
    ("c1", None, "demo_tang", "我想展示校园话题：一张照片、一句记录，也能引出很多共同回忆。", "joy"),
    ("c2", "c1", "lin", "从晚自习后的操场开始怎么样？大家都有不同的路线。", "calm"),
    ("c3", "c2", "demo_wen", "我会走到看台最后一排，那里能听清风吹树叶的声音。", "calm"),
    ("c4", "c3", "demo_xu", "我会绕到图书馆背面，那里的路灯像一串小小的书签。", "joy"),
    ("c2b", "c1", "demo_lu", "我想补充一条雨天路线，最好有可以避雨的长廊。", "think"),
    ("d1", None, "you", "我想展示情绪标签，同一个话题里也可以有完全不同的感受。", "think"),
    ("d2", "d1", "demo_xu", "比如汇报前我有一点紧张，但看到功能一个个跑通又会安心。", "fear"),
    ("d3", "d2", "demo_chen", "那就先把演示顺序列出来，再一起走一遍，紧张会具体很多。", "calm"),
    ("d4", "d3", "demo", "好，最后用这棵树收尾：功能怎样连起来，讨论就怎样继续。", "joy"),
    ("d2b", "d1", "demo_wen", "我更想保留那些安静的记录，今天没有结论也值得被听见。", "sorrow"),
    ("d3b", "d2b", "demo_qiao", "同意，能认真听见彼此，本身就是一个值得展示的结果。", "calm"),
]

MAIN_ECHO_TEXT = {
    "a1": "可以先把问题写在卡片上，大家选一张自己感兴趣的，再坐到一起聊。",
    "a2": "卡片上要不要加一句背景？只有一个问题，别人可能不知道从哪里接话。",
    "a3": "我有点担心问题太大，比如“毕业以后怎么办”，一小时肯定聊不完。",
    "a4": "那就试着缩小范围，比如“这学期怎么找到一次合适的实习”。",
    "a5": "我可以分享投简历的经历，但每个人的方向不同，答案可能也不同。",
    "a6": "我们可以先交换各自试过的方法，把有帮助的线索记下来。",
    "a7": "卡片背面留一个空白区，结束时每个人写下一个准备尝试的行动。",
    "a8": "我愿意先试试！下周再碰面的时候，还能聊聊那个行动有没有用。",
    "a3b": "也可以放几张轻一点的问题卡，让刚来的同学先热身。",
    "a4b": "比如“最近在哪本书里读到一句想和别人讨论的话”，这个我很想听。",
    "b1": "地点我推荐图书馆一楼的讨论区，周末人少，也有可以写字的桌子。",
    "b2": "图书馆需要预约吗？我怕大家到了以后才发现不能坐那么多人。",
    "b3": "我问过前台，四人以上的小组要提前登记，可以先预约两张桌子。",
    "b4": "那我周三去确认，报名时先按八个人准备，人数多了再加一场。",
    "b2b": "天气好的话也可以在银杏树旁边，不过下雨时得有备用地点。",
    "b3b": "室外轻松一点，声音也容易散，分享经历时可能听不清。",
    "b4b": "第一场先放室内吧，结束以后想继续聊天的人再一起去散步。",
    "c1": "我想做一个小海报，大家可以把自己带来的书、照片或者手账拍进去。",
    "c2": "照片要提前征得同意。有些同学只是想聊天，不一定愿意出现在海报里。",
    "c3": "可以只拍桌上的物品和手写卡片，人物照片另外询问。",
    "c4": "这个方式挺好，我有一本写满批注的小说，可以拿来当第一张素材。",
    "c2b": "海报上加清楚时间、地点和报名方式就够了，手机上也要能一眼看清。",
    "d1": "我有兴趣，但第一次参加陌生活动会紧张，能不能允许先旁听？",
    "d2": "同感，我常常要听别人聊一会儿，才知道自己能分享些什么。",
    "d3": "可以准备一张“想说的时候再加入”的卡片，让主持人别挨个点名。",
    "d4": "记下了，报名表加上旁听选项，也允许中途休息，第一场轻松一点。",
    "d2b": "我还担心讨论变成互相给建议，有时只是想把困惑讲出来。",
    "d3b": "开始前可以先问一句“你想听建议，还是想让我们先听你说”，这样舒服很多。",
}
MAIN_TREE = [
    (key, parent, writer, MAIN_ECHO_TEXT[key], tone)
    for key, parent, writer, _, tone in LEGACY_MAIN_TREE
]
LEGACY_ECHO_TEXT = {item[0]: item[3] for item in LEGACY_MAIN_TREE}

DISCUSSIONS = [
    (
        "campus", "demo_tang", "joy",
        "校园路线征集：从图书馆到食堂，你会走最快的那条路，还是会绕过那棵银杏树？我想做一张由大家的回忆拼起来的校园地图。",
        [
            ("a1", None, "lin", "我会绕过银杏树，傍晚从树下走过去像穿过一层金色滤镜。", "joy"),
            ("a2", "a1", "demo_xu", "树旁的长椅也值得标出来，适合读完一章书后坐一会儿。", "calm"),
            ("a3", "a2", "demo", "把地点和一段小故事放在一起，地图就能变成一份校园记忆。", "think"),
            ("a2b", "a1", "ke", "下雨时我会选东侧长廊，虽然远一点，但鞋不会湿。", "calm"),
            ("b1", None, "demo_lu", "我想标出无障碍路线，有些台阶在普通地图上看不出来。", "think"),
            ("b2", "b1", "demo_qiao", "这个角度很重要，也可以加上夜间照明好的路段。", "think"),
            ("b3", "b2", "you", "下周一起实地走一次，记录路线和步行时间。", "joy"),
            ("c1", None, "demo_wen", "我投食堂后门一票，那里的桂花香能把晚课的疲惫吹散。", "calm"),
        ],
    ),
    (
        "future", "you", "think",
        "如果未来每个人都有一个 AI 助手，你希望它帮你完成任务，还是帮你发现自己还没问过的问题？今天想认真收集两种答案。",
        [
            ("a1", None, "demo_chen", "我希望它先把重复工作做好，让我有时间想更复杂的问题。", "think"),
            ("a2", "a1", "demo_lu", "但如果我们把判断也一起交出去，会不会慢慢失去提问的习惯？", "fear"),
            ("a3", "a2", "lin", "也许可以要求它先给线索，让人自己完成最后一步判断。", "think"),
            ("a4", "a3", "demo", "像结对编程那样，一起讨论，并保留选择背后的理由。", "think"),
            ("b1", None, "demo_xu", "我希望它提醒我不同的可能，尤其是那些与我习惯相反的答案。", "calm"),
            ("b2", "b1", "demo_qiao", "前提是能够解释信息从哪里来，出错时也有纠正入口。", "think"),
            ("b3", "b2", "you", "所以“可追溯”可能比“总能给答案”更值得期待。", "joy"),
            ("c1", None, "ke", "我的第一个愿望比较简单：别让我调试三小时只找到一个逗号。", "joy"),
        ],
    ),
    (
        "reading", "demo_xu", "calm",
        "读书时我会在页边写下问题，过几天再回来回答。你们更喜欢摘抄句子，还是记录当时没有想明白的事？",
        [
            ("a1", None, "demo", "我会先写下问题，答案变化的过程有时比摘抄更有意思。", "think"),
            ("a2", "a1", "lin", "我在同一页写过三次不同答案，后来才发现是自己的经历变了。", "calm"),
            ("a3", "a2", "demo_wen", "书页像一个时间坐标，能找到以前那个读到这里的自己。", "sorrow"),
            ("a4", "a3", "demo_xu", "下次重读时，也许可以给那时的自己留一条新的回声。", "joy"),
            ("b1", None, "demo_tang", "我会夹一张小票，看到日期就能想起读书那天去了哪里。", "joy"),
            ("b2", "b1", "ke", "这比精确的页码还具体，原来生活也可以做索引。", "think"),
            ("b2b", "b1", "you", "我夹过一片落叶，不过后来发现它比情节更容易碎。", "sorrow"),
            ("c1", None, "demo_chen", "技术书我记可验证的问题，小说就留一句最想分享的话。", "think"),
        ],
    ),
    (
        "night", "demo_wen", "calm",
        "深夜电台：留一句今天最想对自己说的话。我先来——没完成的事情可以明天继续，今天认真走过的路也算数。",
        [
            ("a1", None, "demo_tang", "今天的小组任务终于跑通了，想把这个小小的开心记下来。", "joy"),
            ("a2", "a1", "demo", "辛苦了，那个一起盯着屏幕等结果的瞬间很值得记住。", "joy"),
            ("a3", "a2", "demo_chen", "我截了最后一次通过的结果，准备留在项目记录里。", "think"),
            ("b1", None, "demo_xu", "今天有点累，所以决定把待办列表暂时合上。", "sorrow"),
            ("b2", "b1", "lin", "给自己留一段不用完成任何任务的时间，也很重要。", "calm"),
            ("b3", "b2", "you", "我已经泡好热茶，准备听完这首歌就休息。", "calm"),
            ("b2b", "b1", "demo_qiao", "有些急着得到的答案，睡醒以后会更清楚。", "calm"),
            ("c1", None, "ke", "给明天的自己：先吃早餐，再开电脑。", "joy"),
        ],
    ),
]

SHORT_POSTS = [
    ("coding", "demo", "think", 2, "把一个大问题拆成三个可验证的小问题，今天终于感觉自己是在理解代码，而不是追着报错跑。"),
    ("campus", "lin", "joy", 3, "食堂阿姨记住了我不要香菜。一个小小的细节，让忙碌的一天突然有了温度。"),
    ("reading", "demo", "calm", 5, "读到一段很喜欢的话，没有急着摘抄，而是合上书想了五分钟。留白也是阅读的一部分。"),
    ("future", "demo_lu", "fear", 7, "新工具越来越快，我却想慢一点理解它。会使用和真正知道它为什么工作，是两种不同的安心。"),
    ("night", "ke", "sorrow", 9, "雨停以后，窗外安静得像按下了暂停键。原来一天结束的时候，也可以不急着给它评分。"),
    ("coding", "demo_chen", "joy", 12, "删掉一段重复代码以后，测试还是全部通过。今天最有成就感的动作，居然是按了退格键。"),
    ("campus", "demo", "calm", 16, "晚课结束以后绕着操场走了一圈。没有新消息，没有新任务，只有脚步和风。"),
    ("reading", "demo_xu", "think", 20, "一本书最好的讨论，也许从“我不同意这里”开始。想听听你们最近读到的不同意见。"),
    ("future", "you", "anger", 24, "希望每个产品都认真对待“取消”按钮。用户愿意留下，应该来自信任，而不是找不到出口。"),
    ("night", "demo", "joy", 29, "项目里又多了一条真正能跑通的流程。把小进步留在这里，下次焦虑时回来看看。"),
]

DEMO_IMAGES = {
    MAIN_CONTENT: ("ripple-1-a.jpeg",),
    DISCUSSIONS[0][3]: ("ripple-2-a.jpeg",),
    DISCUSSIONS[1][3]: ("ripple-4-a.jpeg",),
    DISCUSSIONS[2][3]: ("ripple-2-a.jpeg",),
    DISCUSSIONS[3][3]: ("ripple-3-a.jpeg", "ripple-3-d.jpeg"),
    SHORT_POSTS[0][4]: ("ripple-6-a.jpeg",),
    SHORT_POSTS[2][4]: ("ripple-2-a.jpeg",),
    SHORT_POSTS[4][4]: ("ripple-3-a.jpeg",),
}


def seed(db: Session, now: datetime) -> dict:
    added = Counter()
    users = {user.username: user for user in db.scalars(select(User).where(User.role == "user"))}
    topics = {topic.slug: topic for topic in db.scalars(select(Topic))}
    emotions = set(db.scalars(select(Emotion.code)))
    required_users = {"demo", "lin", "ke", "you"}
    if required_users - users.keys() or {"coding", "campus", "future", "reading", "night"} - topics.keys():
        raise RuntimeError("The standard development users and topics are required")
    if {"think", "joy", "calm", "fear", "sorrow", "anger"} - emotions:
        raise RuntimeError("The standard emotion dictionary is required")

    for username, nickname, bio, mood in NEW_USERS:
        if username not in users:
            users[username] = User(
                username=username, nickname=nickname, bio=bio, mood_tone=mood,
                password_hash=hash_password("demo123456"), created_at=now - timedelta(days=35),
            )
            db.add(users[username])
            added["users"] += 1
    db.flush()
    actors = [users[name] for name in ["demo", "lin", "ke", "you", *(item[0] for item in NEW_USERS)]]
    posts = []
    all_echoes = []
    main_id = None
    max_depth = 0

    def make_discussion(slug, author, mood, content, created_at, tree):
        nonlocal main_id, max_depth
        post = db.scalar(select(Ripple).where(
            Ripple.user_id == users[author].id, Ripple.content == content,
        ).order_by(Ripple.id).limit(1))
        if post is None and content == MAIN_CONTENT:
            post = db.scalar(select(Ripple).where(
                Ripple.user_id == users[author].id, Ripple.content == LEGACY_MAIN_CONTENT,
                Ripple.status == "published",
            ).order_by(Ripple.id).limit(1))
            if post is not None:
                post.content = content
                post.topic_id = topics[slug].id
                added["refreshed_posts"] += 1
        if post is None:
            post = Ripple(
                user_id=users[author].id, topic_id=topics[slug].id, content=content,
                emotion_code=mood, status="published", created_at=created_at,
            )
            db.add(post)
            db.flush()
            added["ripples"] += 1
        if content == MAIN_CONTENT:
            main_id = post.id
        if post.status == "published" and not post.images and content in DEMO_IMAGES:
            names = DEMO_IMAGES[content]
            for name in names:
                if not (Path(settings.upload_dir) / name).is_file():
                    raise FileNotFoundError(f"Missing demonstration image: {name}")
            post.images = [f"{settings.upload_url_prefix.rstrip('/')}/{name}" for name in names]
            added["illustrated_posts"] += 1
        posts.append(post)
        existing = {
            (echo.parent_echo_id, echo.content): echo
            for echo in db.scalars(select(Echo).where(Echo.root_ripple_id == post.id))
        }
        nodes = {}
        depths = {}
        for index, (key, parent, writer, text, tone) in enumerate(tree):
            if len(text) > 200:
                raise ValueError("An echo exceeds 200 characters")
            parent_id = nodes[parent].id if parent else None
            depth = depths[parent] + 1 if parent else 1
            if depth > MAX_ECHO_DEPTH:
                raise ValueError("An echo exceeds the supported tree depth")
            max_depth = max(max_depth, depth)
            echo = existing.get((parent_id, text))
            if echo is None and content == MAIN_CONTENT:
                legacy = existing.get((parent_id, LEGACY_ECHO_TEXT[key]))
                if legacy is not None and legacy.user_id == users[writer].id:
                    legacy.content = text
                    echo = legacy
                    added["refreshed_echoes"] += 1
            if echo is None:
                echo = Echo(
                    root_ripple_id=post.id, parent_echo_id=parent_id,
                    user_id=users[writer].id, content=text, emotion_code=tone,
                    created_at=post.created_at + timedelta(minutes=index + 1),
                )
                db.add(echo)
                db.flush()
                recipient_id = nodes[parent].user_id if parent else post.user_id
                if recipient_id != echo.user_id:
                    # Imported history is read so the demo inbox remains usable.
                    db.add(Notification(
                        recipient_id=recipient_id, actor_id=echo.user_id, echo_id=echo.id,
                        kind="reply" if parent else "echo",
                        created_at=echo.created_at, read_at=echo.created_at,
                    ))
                added["echoes"] += 1
            nodes[key] = echo
            depths[key] = depth
            all_echoes.append(echo)

    make_discussion("campus", "demo", "think", MAIN_CONTENT, now - timedelta(minutes=90), MAIN_TREE)
    for index, (slug, author, mood, content, tree) in enumerate(DISCUSSIONS):
        make_discussion(slug, author, mood, content, now - timedelta(hours=4 + index * 6), tree)

    for index, (slug, author, mood, age, content) in enumerate(SHORT_POSTS):
        first = actors[(index + 1) % len(actors)].username
        second = actors[(index + 3) % len(actors)].username
        tree = [
            ("a1", None, first, "这个片刻值得记住。你是从哪一个细节开始注意到它的？", "think"),
            ("a2", "a1", author, "大概是在停下来认真看一眼的时候，以前总会直接略过。", mood),
            ("b1", None, second, "我也遇到过类似的时刻，想把自己的故事接在这里。", "calm"),
        ]
        make_discussion(slug, author, mood, content, now - timedelta(days=age, hours=1), tree)

    def add_unique(model, filters, values):
        if db.scalar(select(model.id).filter_by(**filters)) is None:
            db.add(model(**filters, **values))
            added[model.__tablename__] += 1

    for index, post in enumerate(posts):
        others = [actor for actor in actors if actor.id != post.user_id]
        for actor in others[:3 + index % 6]:
            add_unique(Like, {"user_id": actor.id, "ripple_id": post.id},
                       {"created_at": min(now, post.created_at + timedelta(minutes=30))})
        for actor in others[1:3]:
            add_unique(Collection, {"user_id": actor.id, "ripple_id": post.id},
                       {"created_at": min(now, post.created_at + timedelta(minutes=35))})

    for index, echo in enumerate(all_echoes):
        others = [actor for actor in actors if actor.id != echo.user_id]
        for actor in others[:1 + index % 3]:
            add_unique(EchoLike, {"user_id": actor.id, "echo_id": echo.id},
                       {"created_at": min(now, echo.created_at + timedelta(minutes=2))})

    # Include the demonstration feed's authors and topics in the existing demo account.
    for actor in actors[1:]:
        add_unique(Follow, {"follower_id": users["demo"].id, "followee_id": actor.id},
                   {"created_at": now - timedelta(days=1)})
    for slug in ("coding", "campus", "reading"):
        key = (users["demo"].id, topics[slug].id)
        if db.get(TopicSubscription, key) is None:
            db.add(TopicSubscription(user_id=key[0], topic_id=key[1]))
            added["topic_subscriptions"] += 1

    db.flush()
    return {
        "added": dict(added), "demo_ripple_ids": [post.id for post in posts],
        "main_ripple_id": main_id, "main_branches": 4, "main_echoes": len(MAIN_TREE),
        "total_demo_echoes": len(all_echoes), "maximum_depth": max_depth,
        "main_url": f"http://127.0.0.1:5173/ripples/{main_id}",
    }


def main():
    engine = create_engine(settings.database_url, echo=False)
    # One connection owns the advisory lock across commits and releases it in finally.
    with engine.connect() as connection:
        if connection.scalar(select(func.get_lock(LOCK_NAME, 10))) != 1:
            raise RuntimeError("Another demo-data import is running")
        connection.commit()
        try:
            with Session(bind=connection) as db:
                with db.begin():
                    result = seed(db, datetime.now())
            import json
            print(json.dumps(result, ensure_ascii=True))
        finally:
            connection.execute(select(func.release_lock(LOCK_NAME)))
            connection.commit()
    engine.dispose()


if __name__ == "__main__":
    main()
