# KGBERS — 知识图谱驱动的个性化在线教育推荐系统

> 基金项目「知识图谱驱动的个性化在线教育推荐系统研究」的研究脚手架。
>
> ✅ 应用可启动、页面可访问、测试通过（`pytest` 全绿）。推荐算法为纯 Python 混合实现（内容 + 协同 + 可选知识图谱），ML/NLP 重型模块仍在路线图中。首次上手请先阅读 [TODO.md](TODO.md) 与下方「路线图」。

## 项目简介

KGBERS（Knowledge Graph based Education Recommendation System）尝试用 **Neo4j 教育知识图谱 + SQLite 学习者数据** 为在线学习（MOOC）场景提供个性化课程推荐。原始需求见 `prompts.txt`。

规划中的六大模块：

1. 教育知识图谱构建（课程知识点、先修关系等）
2. 学习者建模（知识水平、兴趣、画像）
3. 课程内容理解（抓取、主题建模、课程知识图谱）
4. 个性化推荐引擎（语义相似度、路径/难度约束、排序）
5. 用户交互界面（知识地图、推荐列表/详情、进度跟踪）
6. 系统运维与评估（A/B 测试、满意度评估）

**现状**：前 5 个模块均有可运行的骨架实现；推荐引擎为内容/协同/图谱混合（无 Neo4j 时自动降级）。第 6 个模块（A/B 测试、满意度评估）尚未实现，见「路线图」。

## 技术栈

| 层 | 选型 |
| --- | --- |
| Web 框架 | Flask 2.0.1（`flask-sqlalchemy` / `flask-login` / `flask-wtf` / `flask-bootstrap`） |
| 关系数据库 | SQLite（`data/sqlite/app.db`） |
| 图数据库 | Neo4j（通过 `py2neo` 访问，可选；不可用时降级） |
| 数据处理 | 纯 Python（推荐/主题抽取）；numpy / pandas / scikit-learn / gensim / nltk 列为预留依赖 |
| 测试 | pytest |
| Python | 3.9 |

## 目录结构

```
KGBERS/
├── .github/workflows/ci.yml     # GitHub Actions：安装 requirements-dev.txt 并运行 pytest
├── app/
│   ├── __init__.py              # create_app()、db / login_manager / bootstrap 单例、user_loader、db.create_all()
│   ├── commands.py              # Flask CLI：flask seed-db
│   ├── models/                  # User / Course / Recommendation（SQLAlchemy）+ KnowledgeGraph（py2neo）
│   ├── routes/                  # 蓝图：main / user / course / recommendation / knowledge_graph
│   ├── services/                # 学习者建模、课程分析、混合推荐、知识图谱服务
│   ├── utils/                   # neo4j_utils.py（get_neo4j_db）/ sqlite_utils.py
│   ├── templates/               # Jinja2 模板
│   └── static/                  # css / js
├── tests/                       # pytest 用例 + conftest.py
├── data/                        # 运行时生成（gitignored）
├── config.py                    # 配置类与 config 字典
├── run.py                       # 入口（加载 .env 后 create_app）
├── requirements.txt             # 运行时依赖（含重型 ML 包）
├── requirements-dev.txt         # 测试/CI 精简依赖（不含 ML 包）
├── pytest.ini
├── .env.example                 # 环境变量样例
├── Dockerfile                   # gunicorn run:app
├── prompts.txt                  # 原始基金课题需求（中文）
├── README.md / TODO.md / AGENTS.md
└── LICENSE
```

### 蓝图与路由前缀

| 蓝图 | 前缀 | 主要路由 |
| --- | --- | --- |
| `main` | 无 | `/`、`/about`、`/contact` |
| `user` | `/user` | `/register`、`/login`、`/logout`、`/profile`、`/users` |
| `course` | `/course` | `/courses`、`/courses/<id>`、`/courses/add`、`/courses/search`、`/courses/filter`、`/courses/top_rated` |
| `recommendation` | `/recommendation` | `/recommendations`、`/recommendations/for-you`、`/recommendations/course/<id>`、`/recommendations/top`、`/recommendations/add`、`/recommendations/<id>`（PUT/DELETE） |
| `knowledge_graph` | `/knowledge-graph` | `/knowledge_graph`、`/knowledge_graph/concept[...]` |

## 快速开始

```bash
# 1. 安装依赖（建议 Python 3.9 虚拟环境）
pip install -r requirements.txt

# 2. 可选：复制环境变量样例
cp .env.example .env

# 3. 启动开发服务器（0.0.0.0:5000；data/sqlite 会自动创建并建表）
python run.py

# 4. 可选：写入示例课程 / 演示用户 / 推荐
FLASK_APP=run.py flask seed-db      # 演示账号 demo / demo1234
```

- 也可用 `FLASK_CONFIG=testing python run.py` 切换配置；`default` → `DevelopmentConfig`。
- Neo4j 可选：`get_neo4j_db()` 读取 `NEO4J_URI/USER/PASSWORD`（默认 `bolt://localhost:7687` / `neo4j` / `password`）。知识图谱相关功能在 Neo4j 不可用时降级（空图 / 图谱信号置 0），不影响其他页面。
- `.env` 会被 `run.py` 自动加载；也可直接在 shell 设置 `SECRET_KEY`、`DATABASE_URL`、`TEST_DATABASE_URL`、`NEO4J_*`、`FLASK_CONFIG`。

## 测试

```bash
FLASK_CONFIG=testing pytest tests     # 27 passed
```

- 用例为 pytest 函数风格，`tests/conftest.py` 提供 `app` / `client` fixture，并禁用真实 Neo4j 访问。
- `TEST_DATABASE_URL` 指定测试库（默认 `data/sqlite/test.db`）。
- CI 使用精简的 `requirements-dev.txt`（避免 pandas 1.3.3 等重型包在部分平台的构建问题）。

## 推荐算法

`RecommendationService.recommend_for_user()` 组合三类信号（权重 0.5 / 0.3 / 0.2）：

1. **内容**：候选课程类别与用户已评价课程类别的匹配度、难度接近度。
2. **协同/质量**：候选课程在所有用户评分中的平均值。
3. **知识图谱**：候选课程与用户已学课程在 Neo4j 中共享 `HAS_TOPIC` 主题的 Jaccard 相似度（Neo4j 不可用时为 0）。

`CourseAnalysisService._perform_topic_modeling` 使用词频关键词抽取（中英文混合，无第三方 NLP 依赖）。

## 路线图 / 未来工作

以下为 `prompts.txt` 中规划但尚未实现的部分：

- **学习路径规划**：基于先修关系生成推荐学习序列。
- **A/B 测试**：在线实验与不同推荐策略的对照评估。
- **满意度评估**：问卷 / 反馈采集与推荐效果分析。
- **重型主题建模**：以 LDA / 句法分析替换当前的关键词抽取，接入 `gensim` / `nltk`。
- **真实 MOOC 数据接入**：替换 `CourseAnalysisService.fetch_course_data` 的占位 URL。
- **数据库迁移**：当前依赖 `db.create_all()`，如需演进可引入 Flask-Migrate。

## 文档说明

- `prompts.txt`：原始基金课题需求（中文），是理解设计意图的最佳来源。
- `file_structure.md`：项目目录结构说明。
- `AGENTS.md`：面向 AI 协作/自动化工具的仓库操作要点。
- `TODO.md`：已完成与待办事项。

## 许可证

MIT License，见 [LICENSE](LICENSE)。
