# KGBERS — 知识图谱驱动的个性化在线教育推荐系统

> 基金项目「知识图谱驱动的个性化在线教育推荐系统研究」的研究脚手架。
>
> ✅ 应用可启动、页面可访问、测试通过（`pytest` 全绿）。六大模块（知识图谱、学习者建模、课程分析、混合推荐、交互界面、A/B 评估）均有可运行实现；`prompts.txt` 规划的功能已全部落地，重型 ML 为可选增强。首次上手请先阅读 [TODO.md](TODO.md)。

## 项目简介

KGBERS（Knowledge Graph based Education Recommendation System）尝试用 **Neo4j 教育知识图谱 + SQLite 学习者数据** 为在线学习（MOOC）场景提供个性化课程推荐。原始需求见 `prompts.txt`。

规划中的六大模块：

1. 教育知识图谱构建（课程知识点、先修关系等）
2. 学习者建模（知识水平、兴趣、画像）
3. 课程内容理解（抓取、主题建模、课程知识图谱）
4. 个性化推荐引擎（语义相似度、路径/难度约束、排序）
5. 用户交互界面（知识地图、推荐列表/详情、进度跟踪）
6. 系统运维与评估（A/B 测试、满意度评估）

**现状**：六大模块均有可运行的实现。推荐引擎为内容/协同/图谱混合（无 Neo4j 时自动降级）；学习路径、A/B 测试与满意度评估已落地；LDA 主题建模与真实数据导入为可选/可配置增强。

## 技术栈

| 层 | 选型 |
| --- | --- |
| Web 框架 | Flask 2.0.1（`flask-sqlalchemy` / `flask-login` / `flask-wtf`（CSRF） / `flask-bootstrap`） |
| 关系数据库 | SQLite（`data/sqlite/app.db`） |
| 图数据库 | Neo4j（通过 `py2neo` 访问，可选；不可用时降级） |
| 数据处理 | 纯 Python（推荐/关键词抽取）；安装 `requirements-ml.txt` 后启用 gensim LDA / nltk |
| 数据库迁移 | Flask-Migrate / Alembic |
| 测试 | pytest |
| Python | 3.9 |

## 目录结构

```
KGBERS/
├── .github/workflows/ci.yml     # GitHub Actions：安装 requirements-dev.txt、迁移冒烟、运行 pytest
├── app/
│   ├── __init__.py              # create_app()、db/migrate/login_manager/bootstrap 单例、user_loader
│   ├── commands.py              # CLI：flask seed-db / import-courses / experiment-report
│   ├── models/                  # User / Course / Recommendation / experiment 三模型 + KnowledgeGraph（py2neo）
│   ├── routes/                  # 蓝图：main / user / course / recommendation / knowledge_graph
│   ├── services/                # 学习者建模、课程分析、混合推荐、学习路径、实验、主题建模、课程导入
│   ├── samples/                 # 内置课程样例 mooc_courses.json
│   ├── utils/                   # neo4j_utils.py（get_neo4j_db）/ sqlite_utils.py
│   ├── templates/               # Jinja2 模板
│   └── static/                  # css / js
├── migrations/                  # Alembic 迁移（baseline）
├── tests/                       # pytest 用例 + conftest.py
├── data/                        # 运行时生成（gitignored）
├── config.py                    # 配置类与 config 字典
├── run.py                       # 入口（加载 .env 后 create_app）
├── requirements.txt             # 运行时依赖（含重型 ML 包）
├── requirements-dev.txt         # 测试/CI 精简依赖（不含 ML 包）
├── requirements-ml.txt          # 可选 LDA/NLP 依赖（gensim/nltk/numpy/scipy）
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
| `course` | `/course` | `/courses`、`/courses/<id>`、`/courses/<id>/path`、`/courses/add`、`/courses/search`、`/courses/filter`、`/courses/top_rated` |
| `recommendation` | `/recommendation` | `/recommendations`、`/recommendations/for-you`、`/recommendations/feedback`、`/recommendations/click/<id>`、`/recommendations/experiments/report`、`/recommendations/course/<id>`、`/recommendations/top`、`/recommendations/add`、`/recommendations/<id>`（PUT/DELETE） |
| `knowledge_graph` | `/knowledge-graph` | `/knowledge_graph`、`/knowledge_graph/concept[...]` |

## 快速开始

```bash
# 1. 安装依赖（建议 Python 3.9 虚拟环境）
pip install -r requirements.txt

# 2. 可选：复制环境变量样例
cp .env.example .env

# 3. 应用数据库迁移（开发/生产；测试环境自动建表）
FLASK_APP=run.py flask db upgrade

# 4. 启动开发服务器（0.0.0.0:5000）
python run.py

# 5. 可选：写入示例数据 / 导入课程
FLASK_APP=run.py flask seed-db          # 课程 + 演示账号 demo/demo1234 + 先修关系
FLASK_APP=run.py flask import-courses   # 从配置数据源/内置样例导入
```

- 也可用 `FLASK_CONFIG=testing python run.py` 切换配置；`default` → `DevelopmentConfig`。
- Neo4j 可选：`get_neo4j_db()` 读取 `NEO4J_URI/USER/PASSWORD`（默认 `bolt://localhost:7687` / `neo4j` / `password`）。知识图谱相关功能在 Neo4j 不可用时降级（空图 / 图谱信号置 0），不影响其他页面。
- `.env` 会被 `run.py` 自动加载；也可直接在 shell 设置 `SECRET_KEY`、`DATABASE_URL`、`TEST_DATABASE_URL`、`NEO4J_*`、`COURSE_DATA_URLS`、`FLASK_CONFIG`。

## 测试

```bash
FLASK_CONFIG=testing pytest tests     # 48 passed, 1 skipped
```

- 用例为 pytest 函数风格，`tests/conftest.py` 提供 `app` / `client` fixture，并禁用真实 Neo4j 访问。
- `TEST_DATABASE_URL` 指定测试库（默认 `data/sqlite/test.db`）。
- CI 使用精简的 `requirements-dev.txt`（避免 pandas 1.3.3 等重型包在部分平台的构建问题），并执行 `flask db upgrade` 迁移冒烟。
- LDA 用例在未安装 `requirements-ml.txt` 时自动 skip（`pytest.importorskip` 语义）。

## 推荐算法

`RecommendationService.recommend_for_user()` 组合三类信号（权重 0.5 / 0.3 / 0.2）：

1. **内容**：候选课程类别与用户已评价课程类别的匹配度、难度接近度。
2. **协同/质量**：候选课程在所有用户评分中的平均值。
3. **知识图谱**：候选课程与用户已学课程在 Neo4j 中共享 `HAS_TOPIC` 主题的 Jaccard 相似度（Neo4j 不可用时为 0）。

`CourseAnalysisService._perform_topic_modeling` 默认使用词频关键词抽取；安装 `requirements-ml.txt`（gensim/nltk）后自动改用 **gensim LDA** 主题建模（`TopicModelService`），依赖缺失或语料不足时回退。

## 学习路径规划

`LearningPathService` 基于课程的先修关系（`course_prerequisites` 关联表 / `Course.prerequisites`）生成学习序列：

- 收集目标课程的传递先修课程，做 Kahn 拓扑排序（先修在前），同层按难度升序、评分降序稳定排序，并检测环。
- 登录用户访问时标记已完成课程。
- 页面：`GET /course/courses/<id>/path`（从课程详情进入）。

## A/B 测试与满意度评估

`ExperimentService` 提供可复现的在线实验：

- **分组**：按 `md5(experiment:user_id)` 确定性分配 `control`（按评分排序）/ `treatment`（混合推荐），首次访问落库。
- **反馈**：`for-you` 页面提交星级 + 评论（`POST /recommendation/recommendations/feedback`）；分组以服务端分配为准。
- **指标**：点击课程时上报 `POST /recommendation/recommendations/click/<id>`；曝光去重，报告输出曝光 / 点击与 CTR、平均满意度；报告页 `GET /recommendation/recommendations/experiments/report` 或 CLI `flask experiment-report`。
- **安全**：启用 Flask-WTF `CSRFProtect`，表单与 JS 请求携带 token（测试环境自动关闭）。

## 课程数据导入

`CourseImportService` 支持从可配置数据源导入课程：

- 数据源为 JSON（对象含 `courses`/`results`，或数组），支持 URL 或本地文件；字段别名自动映射（如 `name→title`、`level→difficulty`）。
- 配置：环境变量 `COURSE_DATA_URLS`（逗号分隔）；为空时回退到内置样例 `app/samples/mooc_courses.json`。
- 命令：`flask import-courses [--source URL|FILE ...]`（按标题去重）。

## 数据库迁移

使用 Flask-Migrate/Alambic 管理 schema（`migrations/`）：

```bash
FLASK_APP=run.py flask db upgrade      # 应用迁移(开发/生产)
FLASK_APP=run.py flask db migrate -m "message"   # 修改模型后生成迁移
```

测试环境仍由 `create_app()` 中的 `db.create_all()` 自动建表。

## 文档说明

- `prompts.txt`：原始基金课题需求（中文），是理解设计意图的最佳来源。
- `file_structure.md`：项目目录结构说明。
- `AGENTS.md`：面向 AI 协作/自动化工具的仓库操作要点。
- `TODO.md`：已完成与待办事项。

## 许可证

MIT License，见 [LICENSE](LICENSE)。
