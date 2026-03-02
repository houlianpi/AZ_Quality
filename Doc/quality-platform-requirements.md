# Quality Platform 需求文档

## 1. 项目背景

Edge 团队使用 Azure DevOps (ADO) 管理所有 bugs、test cases 和测试任务。目前数据分散在 ADO 的不同 dashboards 和 queries 中，缺乏统一的视图来支持日常质量活动。

**目标**: 构建一个统一的 Web 平台，整合 ADO 数据，按质量活动组织和展示，提升团队质量管理效率。

**核心痛点**: 数据分散在不同地方，没有统一视图

**成功指标**:
- 节省 Quality FTE 时间
- 数据集中、标准化、透明

**用户规模**: 50+ 人

**上线目标**: MVP 1 个月内可用

---

## 2. 目标用户

| 用户角色 | 使用场景 |
|----------|----------|
| **Quality 同学** | 日常质量活动跟踪、测试执行管理、bug triage |
| **Quality Push 参与的开发** | 查看自己负责的 SLA bugs、了解质量状态 |
| **Team Lead** | 团队质量概览、进度跟踪、资源分配决策 |
| **Bug 负责人** | 跟踪自己的 bugs 状态、SLA deadline |

### 个性化需求

用户登录后可以看到：
- ✅ 只看自己负责的 bugs / tasks
- ✅ 只看自己 team 的数据
- ✅ 自定义 dashboard（选择显示/隐藏整个模块）

---

## 3. 功能模块

### 优先级排序

| 优先级 | 模块 | 原因 |
|--------|------|------|
| **P0** | Quality Push Review | 已有基础，核心功能 |
| **P0** | New Feature 质量跟进 | 用户明确需求 |
| **P0** | 测试执行跟踪 | 用户明确需求 |
| P1 | 实验平台集成 | 找出已 flight 但 bug 未修复的实验 |
| P1 | 测试用例整体情况 | 后续迭代 |
| P1 | 自动化测试运行结果 | 后续迭代 |

---

### 3.1 Quality Push Review (已有基础)

| 子模块 | 数据来源 | 状态 |
|--------|----------|------|
| SLA Bug Review | ADO Query (Blocking/Security/Perf/Disabled/A11y/P0P1) | ✅ 已实现 |
| Bug Triage Queue | ADO Saved Query | ✅ 已实现 |
| OCV/DSAT Review | ADO Dashboard widgets | 🔲 待开发 |
| Bug Escape Rate | TBD | 🔲 待开发 |

---

### 3.2 New Feature 质量跟进

| 子模块 | 描述 | 数据来源 |
|--------|------|----------|
| Feature 任务树 | 展示 Feature → Task → Sub-task 层级 | ADO Work Item Links |
| 子任务状态 | Active/Resolved/Closed 分布 | ADO Work Items |
| 优先级分布 | P0/P1/P2/P3 分布 | ADO Work Items |
| 负责人工作量 | 按 assignee 统计任务数 | ADO Work Items |
| 进度趋势 | 任务完成趋势图 | ADO Work Items (历史) |

**Feature 获取方式**:
- 每个 team 各自维护一个 ADO Query，列出需要跟踪的 Feature
- 每个 team 约 20+ 个 Feature 需要同时跟踪

**展示方式**:
- 列表视图：表格列出所有 Feature 和关键指标（完成率、P0/P1 数量等）
- 问题优先：突出显示"有问题"的 Feature

**"有问题"的 Feature 定义**:
- ⚠️ 完成率低于阈值（如 < 80%）
- ⚠️ 有未解决的 P0 bug/task
- ⚠️ 有未解决的 P1 bug/task
- ⚠️ 超过 15 天没有进展（无状态变更）
- ⚠️ 已 flight 的实验但关联 bug 未修复（需实验平台集成）

---

### 3.3 测试执行跟踪

| 子模块 | 描述 | 数据来源 |
|--------|------|----------|
| 测试计划进度 | 按 test plan 展示执行进度 | ADO Test Plans |
| 测试结果统计 | Pass/Fail/Blocked/Not Run 分布 | ADO Test Plans |
| 每日执行趋势 | 测试执行的时间趋势图 | ADO Test Plans |
| 阻塞分析 | Blocked 用例原因分析 | ADO Test Plans |

**测试类型覆盖**:
- ✅ 手动测试 → 数据在 ADO Test Plans
- ✅ 自动化测试 → 数据在 ADO Pipelines

---

### 3.4 实验平台集成 (P1)

| 子模块 | 描述 | 数据来源 |
|--------|------|----------|
| 实验状态 | 已 flight / 未 flight 实验列表 | 实验平台 (ECS) |
| Bug 关联 | 实验关联的 bug 状态 | ADO Work Item Links |
| 风险识别 | 已 flight 但有未修复 bug 的实验 | 实验平台 + ADO |

**数据关联方式**:
- Bug 和实验通过 ADO Work Item Link 关联

**待确认**:
- [ ] 实验平台 API 访问方式（需进一步调研）

---

### 3.5 测试用例整体情况 (P1)

| 子模块 | 描述 | 数据来源 |
|--------|------|----------|
| 用例总数统计 | 按 area path / suite 统计 | ADO Test Plans |
| 用例状态分布 | Design/Ready/Obsolete | ADO Test Plans |
| 自动化覆盖率 | 自动化 vs 手动用例比例 | ADO Test Plans |
| 用例增长趋势 | 新增用例趋势 | ADO Test Plans |

---

### 3.6 自动化测试运行结果 (P1)

| 子模块 | 描述 | 数据来源 |
|--------|------|----------|
| Pipeline 运行状态 | 最近运行的 pass rate | ADO Pipelines |
| 失败用例分析 | 失败用例列表和原因 | ADO Pipelines |
| Flaky 测试识别 | 不稳定测试识别 | ADO Pipelines (历史分析) |
| 运行趋势 | 自动化稳定性趋势 | ADO Pipelines |

---

## 4. 告警通知

### 4.1 告警场景

| 场景 | 描述 | 优先级 |
|------|------|--------|
| SLA 即将到期 | Bug SLA 剩余 7 天时通知 | P0 |
| 新 P0/P1 分配 | 新的 P0/P1 bug 分配给用户 | P0 |
| Feature 完成率下降 | Feature 完成率低于阈值 | P1 |
| Feature 停滞 | Feature 超过 15 天无进展 | P1 |
| 实验风险 | 已 flight 实验有未修复 bug | P1 |

### 4.2 通知渠道

| 渠道 | 用途 |
|------|------|
| **Email** | 每日/每周汇总报告 |
| **Teams Channel** | 实时告警通知（发到 Team Channel 或 Quality Channel） |

---

## 5. 配置项

### 5.1 Team 配置

每个 Team 需要配置：
- Area Path（用于 bug 过滤）
- Triage Query ID
- **Feature Query ID**（用于 New Feature 跟进）
- **Test Plan IDs**（用于测试执行跟踪）
- **Pipeline IDs**（用于自动化测试结果）
- **Teams Channel Webhook**（用于通知）

目前已有 Team:
- edge-mobile
- edge-mac
- edge-china-consumer

### 5.2 时间范围

| 数据类型 | 默认时间范围 |
|----------|-------------|
| Bug 数据 | 30 天 |
| 测试执行 | 30 天 |
| 趋势图 | 30 天 |

### 5.3 告警阈值

| 阈值项 | 默认值 |
|--------|--------|
| SLA 提前通知 | 7 天 |
| Feature 完成率警戒线 | 80% |
| Feature 停滞天数 | 15 天 |

### 5.4 数据更新频率

- [x] 定时刷新：每 8 小时更新一次

### 5.5 权限控制

- [x] 需要登录认证
- 目的：个性化视图（登录后看自己/team 相关数据）

### 5.6 部署方式

- [x] Cloud 部署

---

## 6. 用户故事

### Quality 同学

> 作为一名 Quality 同学，我希望登录后能看到：
> 1. 我负责的 team 的 SLA bug 状态
> 2. 需要 triage 的 bug 列表
> 3. 当前 sprint 的测试执行进度
> 4. 我跟进的 Feature 的质量状态（特别是有问题的）
>
> 这样我可以快速了解今天需要关注什么。

### 开发同学

> 作为一名参与 Quality Push 的开发，我希望：
> 1. 快速看到分配给我的 SLA bugs
> 2. 了解每个 bug 的 deadline（提前 7 天收到通知）
> 3. 看到我负责的 Feature 的整体进度
>
> 这样我可以合理安排工作优先级。

### Team Lead

> 作为 Team Lead，我希望：
> 1. 看到团队整体的质量指标（SLA pass rate、测试通过率）
> 2. 识别风险点（哪些 Feature 进度落后、哪些 bug 即将过期）
> 3. 了解团队成员的工作量分布
> 4. 在 Teams Channel 收到关键告警
>
> 这样我可以及时调整资源和优先级。

---

## 7. 技术方案 (待定)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Quality Dashboard Platform                    │
├─────────────────────────────────────────────────────────────────┤
│                           Frontend                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Quality  │  │ Feature  │  │   Test   │  │ Experiment│        │
│  │   Push   │  │ Quality  │  │ Tracking │  │ Platform │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│       └─────────────┴──────┬──────┴─────────────┘               │
│                            │                                     │
│  ┌─────────────────────────▼─────────────────────────┐          │
│  │              Authentication Layer                  │          │
│  │         (个性化视图: 用户/Team 数据过滤)            │          │
│  └─────────────────────────┬─────────────────────────┘          │
│                            │                                     │
│  ┌─────────────────────────▼─────────────────────────┐          │
│  │              Notification Service                  │          │
│  │           (Email + Teams Channel)                  │          │
│  └─────────────────────────┬─────────────────────────┘          │
│                            │                                     │
│                    ┌───────▼───────┐                            │
│                    │   Data Layer  │                            │
│                    │ (Cache/DB)    │                            │
│                    │ 8小时刷新一次  │                            │
│                    └───────┬───────┘                            │
│                            │                                     │
│       ┌────────────────────┼────────────────────┐               │
│       ▼                    ▼                    ▼               │
│ ┌───────────┐       ┌───────────┐       ┌───────────┐          │
│ │ ADO Work  │       │ ADO Test  │       │    ADO    │          │
│ │  Items    │       │  Plans    │       │ Pipelines │          │
│ └───────────┘       └───────────┘       └───────────┘          │
│       │                                                         │
│       ▼                                                         │
│ ┌───────────┐                                                   │
│ │Experiment │  (P1 - API 待调研)                                │
│ │ Platform  │                                                   │
│ └───────────┘                                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. MVP 范围

### Phase 1 (MVP) - 目标: 1 个月内

| 功能 | 描述 | 优先级 |
|------|------|--------|
| Quality Push Review | 完善 OCV/DSAT 展示 | P0 |
| New Feature 质量跟进 | Feature 列表 + 子任务分析 + 问题识别 | P0 |
| 用户登录 | 基于 ADO/AAD 认证 | P0 |
| Team 数据过滤 | 按 team 显示相关数据 | P0 |
| 模块显示/隐藏 | 用户可选择显示哪些模块 | P1 |

### Phase 2 - 目标: 2-3 个月

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 测试执行跟踪 | ADO Test Plans 集成 | P0 |
| SLA 告警通知 | Email + Teams Channel | P0 |
| 自动化测试结果 | ADO Pipelines 集成 | P1 |

### Phase 3 - 目标: 3-6 个月

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 实验平台集成 | ECS API 集成（需调研） | P1 |
| 测试用例整体情况 | 用例统计 + 自动化覆盖率 | P1 |
| 趋势分析 | 历史数据趋势图 | P2 |
| 更多告警场景 | Feature 停滞、完成率下降等 | P2 |

---

## 9. 待确认问题

| # | 问题 | 状态 |
|---|------|------|
| 1 | 能否提供一个 Feature Query 的 ID 或 URL 作为示例？ | ⏳ 待回答 |
| 2 | 能否提供一个 Test Plan 的 ID 或 URL 作为示例？ | ⏳ 待回答 |
| 3 | 能否提供一个 Pipeline 的 ID 或 URL 作为示例？ | ⏳ 待回答 |
| 4 | 实验平台 (ECS) 是否有 API？如何访问？ | ⏳ 需调研 |
| 5 | Teams Channel 通知发到哪个 Channel？ | ⏳ 待确认 |

---

## 10. 风险与挑战

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 实验平台 API 不可用 | P1 功能无法实现 | Phase 3 再处理，先做其他功能 |
| ADO API 限流 | 数据更新延迟 | 8 小时刷新 + 本地缓存 |
| 1 个月内交付 MVP | 时间紧张 | 聚焦核心功能，砍掉非必要项 |
| 50+ 用户并发 | 性能问题 | Cloud 部署 + 缓存优化 |

---

*文档创建时间: 2026-02-11*
*最后更新: 2026-02-11*
*版本: v1.0*
