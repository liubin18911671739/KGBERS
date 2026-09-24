# TODO

KGBERS 是一个**可启动、页面可访问、测试通过**的研究脚手架。`P0`（阻断导入/启动）、`P1`（页面可用）、`P2`（工程化/功能）以及 `prompts.txt` 规划的全部模块均已完成。本文件记录已完成事项与后续可选项。

## P0 — 阻断导入 / 启动 ✅ 已完成

- [x] **修复 `app/utils/__init__.py`**：改为无副作用的 `neo4j_utils` 符号再导出，移除包导入时的 Neo4j 连接。
- [x] **修复 `app/services/__init__.py`**：类名更正为 `UserService` / `CourseAnalysisService` / `KnowledgeService`。
- [x] **统一 Neo4j 工具函数**：新增基于 `NEO4J_*` 环境变量的 `get_neo4j_db()`。
- [x] **`app/models/recommendation.py`**：添加 `from datetime import datetime`。
- [x] **service 方法补 `self`**：`recommendation_service.py` / `user_modeling_service.py` / `knowledge_graph_service.py`。
- [x] **统一 `KnowledgeGraph` 构造签名**：`__init__(self, graph)`，关系方法名统一为 `create_relationship`（保留 `create_relation` 别名）。
- [x] **补齐模型的 `save()` / `delete()`**：`User` / `Course` / `Recommendation`。
- [x] **修复 `Dockerfile`**：`FLASK_APP=run.py`，CMD 改为 `gunicorn -b 0.0.0.0:5000 run:app`。
- [x] `user_modeling_service.py` 增加 `UserModelingService = UserService` 别名。

## P1 — 应用可运行 / 页面可用 ✅ 已完成

- [x] **补齐模板**：`about.html`、`contact.html`、`register.html`、`login.html`、`profile.html`、`course_detail.html`、`add_course.html`。
- [x] **`base.html`**：端点更正为 `recommendation.get_user_recommendations`。
- [x] **`index.html` + `main_routes.py`**：循环变量对齐；首页改用 `Course.get_top_rated_courses()`。
- [x] **`course_list.html` + `course_routes.py`**：分页（`Query.paginate`）与 `categories`/`difficulties`；模板对未定义变量做保护。
- [x] **`knowledge_graph.html` + 路由**：传入 `knowledge_graph_data`；fetch 地址改用 `url_for`。
- [x] **推荐前端与接口对齐**：新增 `PUT`/`DELETE /recommendations/<id>`；`scripts.js` 路径补全 `/recommendation` 前缀。
- [x] **注册 `login_manager.user_loader`**。
- [x] **初始化数据库**：创建 `data/sqlite/` 并建表。
- [x] **消除硬编码**：`CourseAnalysisService` 改用 `get_neo4j_db()`。

## P2 — 工程化与功能完善 ✅ 已完成

- [x] **统一测试与实现**：pytest 集成用例 + `conftest.py` fixture；禁用真实 Neo4j。
- [x] **引入 CI**：`.github/workflows/ci.yml`（Python 3.9，`requirements-dev.txt`，`compileall` + 迁移冒烟 + `pytest`）。
- [x] **Flask-Migrate**：`migrations/` baseline；开发/生产 `flask db upgrade`，测试 `db.create_all()`。
- [x] **恢复 `.env` 加载**：`run.py` 启用 `load_dotenv()`；新增 `.env.example`。
- [x] **数据初始化 / 种子脚本**：`flask seed-db`（课程 + 演示用户 + 推荐 + 先修关系）。
- [x] **真实推荐算法**：内容 + 协同 + 可选图谱混合；主题抽取降级实现。
- [x] **知识地图真实数据**：`get_concept_graph` / `get_full_graph` 输出可序列化 d3 `{nodes,links}`。
- [x] **清理文档**：`file_structure.md` / `README.md` / `AGENTS.md` 同步更新。

## 路线图 / prompts.txt 规划模块 ✅ 已完成

- [x] **学习路径规划**：`Course.prerequisites` + `LearningPathService`（拓扑排序）；`GET /course/courses/<id>/path`。
- [x] **A/B 测试与满意度评估**：`ExperimentAssignment` / `Feedback` / `RecommendationEvent` + `ExperimentService`；`for-you` 分组、反馈、点击、报告；`flask experiment-report`。
- [x] **LDA / nltk 主题建模**：`TopicModelService`（gensim LDA，缺失时回退词频）；可选 `requirements-ml.txt`。
- [x] **真实 MOOC 数据接入**：`CourseImportService`（字段别名映射、URL/本地文件、内置样例、去重）；`flask import-courses`。
- [x] **Flask-Migrate 迁移**：见 P2。

## 代码审查修复 ✅ 已完成

- [x] **A/B 分组以服务端为准**：`submit_feedback` 忽略客户端 `variant`，改用 `ExperimentService().assign()`。
- [x] **点击事件落地**：新增 `POST /recommendation/recommendations/click/<id>`，`for_you.html` 点击课程时上报，CTR 不再恒为 0。
- [x] **曝光去重**：`record_impressions` 同一用户/课程/分组只记一次，避免刷新页面膨胀 CTR 分母。
- [x] **保留导入字段 `id`**：`CourseImportService.normalize` 输出 `id`，修复 `analyze_course_topics` 键塌缩为 `None`。
- [x] **批量图谱查询**：`recommend_for_user` 一次 Cypher 取回全部课程主题，消除逐课程 N+1。
- [x] **评分归一化**：质量分 clamp 到 0–5；反馈评分限制 1–5。
- [x] **LDA 状态重置**：`fit` 先清空旧模型，避免语料不足时沿用过期模型。
- [x] **CSRF 保护**：启用 `CSRFProtect`，表单与 JS fetch 携带 token（测试环境关闭）。
- [x] **输入校验**：`add_course`、`recommendations/add`、`modify_recommendation`、`create_concept` 及查询参数避免 500。
- [x] **鉴权补全**：`get_course_recommendations` / `get_top_recommendations` 增加 `@login_required`。
- [x] **分词噪声**：NLTK 路径过滤标点；保留单字中文 token。

## 后续可选项（非必需）

- [ ] 多实验支持：为 `Feedback` / `RecommendationEvent` 增加 `experiment` 维度。
- [ ] 接入真实 MOOC 数据源 URL（当前使用内置样例 / 可配置 `COURSE_DATA_URLS`）。
- [ ] 以 scikit-learn / 更细粒度 NLP 增强主题建模。
