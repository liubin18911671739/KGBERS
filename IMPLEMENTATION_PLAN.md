# IMPLEMENTATION_PLAN.md

## Stage 1: 多实验支持
**Goal**: 为 `Feedback` / `RecommendationEvent` 增加 `experiment` 维度，支持多实验并行统计。
**Success Criteria**:
- 两个模型的 `experiment` 字段存在，migration 可升级/降级。
- `ExperimentService` 的写入/统计均按实验隔离。
- 路由通过 `?experiment=` 查询参数选择实验，默认 `recommendation`。
**Tests**: 多实验隔离测试（不同实验的 report 不串扰）、路由 query 参数测试。
**Status**: Complete

## Stage 2: 真实 MOOC 数据源接入
**Goal**: 示例真实数据源 URL + CSV 解析 + 健壮性增强。
**Success Criteria**:
- `CourseImportService` 支持从真实公开 CSV/JSON URL 拉取并解析。
- 单源失败不影响其他源，失败有日志，最终回退内置样例。
**Tests**: HTTP mock（200/失败）+ CSV 解析 + 别名映射测试。
**Status**: Complete

## Stage 3: sklearn 主题建模增强
**Goal**: sklearn LDA 后端 + 细粒度 NLP（jieba 可选 / nltk lemma / n-gram）。
**Success Criteria**:
- `TopicModelService` 支持 sklearn LDA；`TOPIC_MODEL_BACKEND` 可指定。
- 未安装 sklearn 时自动降级，CI（requirements-dev）下相关测试 skip。
**Tests**: sklearn 后端 fit/extract 测试（未装则 skip）。
**Status**: Complete

## Stage 4: 文档与验证
**Goal**: 同步文档 + 全量测试 + migration 冒烟。
**Success Criteria**: `FLASK_CONFIG=testing pytest tests -q` 全绿；`flask db upgrade` 通过。
**Tests**: 全量 pytest。
**Status**: Complete
