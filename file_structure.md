# 项目目录结构

```
KGBERS/
├── .github/
│   └── workflows/
│       └── ci.yml                     # GitHub Actions:安装 requirements-dev.txt 并运行 pytest
├── app/
│   ├── __init__.py                    # create_app()、db/migrate/login_manager/bootstrap 单例、user_loader
│   ├── commands.py                    # CLI:flask seed-db / import-courses / experiment-report
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                    # User(SQLAlchemy)
│   │   ├── course.py                  # Course(SQLAlchemy,含先修关系 prerequisites)
│   │   ├── recommendation.py          # Recommendation(SQLAlchemy)
│   │   ├── experiment.py              # ExperimentAssignment / Feedback / RecommendationEvent
│   │   └── knowledge_graph.py         # KnowledgeGraph(py2neo 封装,非 SQLAlchemy 模型)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main_routes.py             # 蓝图 main(无前缀)
│   │   ├── user_routes.py             # 蓝图 user(/user)
│   │   ├── course_routes.py           # 蓝图 course(/course,含学习路径)
│   │   ├── recommendation_routes.py   # 蓝图 recommendation(/recommendation,含 for-you/反馈/报告)
│   │   └── knowledge_graph_routes.py  # 蓝图 knowledge_graph(/knowledge-graph)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_modeling_service.py       # UserService(别名 UserModelingService)
│   │   ├── course_analysis_service.py     # CourseAnalysisService
│   │   ├── recommendation_service.py      # RecommendationService(混合推荐)
│   │   ├── knowledge_graph_service.py     # KnowledgeService
│   │   ├── learning_path_service.py       # LearningPathService(拓扑排序)
│   │   ├── experiment_service.py          # ExperimentService(A/B + 反馈 + 报告)
│   │   ├── topic_modeling_service.py      # TopicModelService(LDA / 词频回退)
│   │   └── course_import_service.py       # CourseImportService(JSON 导入)
│   ├── samples/
│   │   └── mooc_courses.json          # 内置课程样例(导入回退)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── neo4j_utils.py             # get_neo4j_graph / get_neo4j_db 等
│   │   └── sqlite_utils.py            # 原生 sqlite3 工具(当前未被路由使用)
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── about.html
│   │   ├── contact.html
│   │   ├── register.html
│   │   ├── login.html
│   │   ├── profile.html
│   │   ├── course_list.html
│   │   ├── course_detail.html
│   │   ├── learning_path.html
│   │   ├── add_course.html
│   │   ├── recommendation_list.html
│   │   ├── for_you.html
│   │   ├── experiment_report.html
│   │   ├── knowledge_graph.html
│   │   └── user_profile.html          # 未被路由使用(路由渲染 profile.html)
│   └── static/
│       ├── css/
│       │   └── styles.css
│       └── js/
│           └── scripts.js
├── migrations/                        # Alembic 迁移(baseline)
│   ├── env.py
│   ├── alembic.ini
│   └── versions/
├── data/                              # 运行时生成,gitignored
│   └── sqlite/
│       ├── app.db
│       └── test.db
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # app / client fixture,禁用真实 Neo4j
│   ├── test_recommendation.py
│   ├── test_recommendation_algorithm.py
│   ├── test_user_modeling.py
│   ├── test_course_analysis.py
│   ├── test_course_import.py
│   ├── test_learning_path.py
│   ├── test_experiment.py
│   ├── test_topic_modeling.py
│   └── test_knowledge_graph.py
├── config.py                          # Config / Development / Testing / Production 与 config 字典
├── run.py                             # 入口:加载 .env 后 create_app
├── requirements.txt                   # 运行时依赖
├── requirements-dev.txt               # 测试 / CI 精简依赖
├── requirements-ml.txt                # 可选 LDA / NLP 依赖
├── pytest.ini
├── .env.example
├── Dockerfile
├── prompts.txt                        # 原始基金课题需求(中文)
├── README.md
├── TODO.md
├── AGENTS.md
└── LICENSE
```

## 说明

- `app`:Flask 应用主包。`models` 定义数据模型与实验/反馈模型;`routes` 定义蓝图与请求处理;`services` 实现核心业务(学习者建模、课程分析、推荐、知识图谱、学习路径、实验、主题建模、课程导入);`samples` 为离线课程样例;`utils` 提供数据库连接工具;`templates` / `static` 为前端资源。
- `migrations`:Flask-Migrate/Alembic 迁移,开发/生产用 `flask db upgrade` 应用。
- `data`:SQLite 数据库文件;测试环境由 `create_app()` 自动建表,目录自动创建。
- `tests`:pytest 用例,`conftest.py` 统一提供 fixture。
- `config.py`:按 `FLASK_CONFIG` 选择配置(`default` → `DevelopmentConfig`)。
- `run.py`:唯一入口,Dockerfile 亦通过 `gunicorn run:app` 使用它。
