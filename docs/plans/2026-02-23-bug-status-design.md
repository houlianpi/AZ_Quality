# Bug Status 数据存储设计

## 概述

本设计聚焦于 Quality Platform 的 Bug Status 模块的**数据存储层**，不涉及 API 和展示层（将在后续阶段实现）。

## 目标

- 通过 Pipeline 定时从 ADO 获取 Bug 数据并存入 MySQL
- 支持每日快照，用于趋势分析
- 每个 Team 独立配置和存储

## 架构

```
ADO (Azure DevOps)
        │
        │ az boards query
        ▼
┌───────────────────┐
│  Pipeline 脚本    │
│  sync_bugs.py     │
├───────────────────┤
│ 1. 读取 team 配置 │
│ 2. 执行 az 命令   │
│ 3. 字段校验       │
│ 4. 写入 MySQL     │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│     MySQL         │
│ edge_mac_bugs     │
│ edge_mobile_bugs  │
│ edge_china_...    │
└───────────────────┘
```

## Bug 分类

### SLA Bugs
- Blocking bugs
- A11y bugs
- Security bugs

### High Priority
- Need Triage
- P0/P1 bugs

## 目录结构

```
quality_platform/
├── config/
│   └── teams/
│       ├── edge_mac.yaml
│       ├── edge_mobile.yaml
│       └── edge_china_consumer.yaml
├── scripts/
│   └── sync_bugs.py          # Pipeline 调用的主脚本
├── app/
│   ├── models/
│   │   └── bug.py            # SQLAlchemy 模型定义
│   └── core/
│       └── database.py       # MySQL 连接
└── ...
```

## Team 配置文件格式

```yaml
# config/teams/edge_mac.yaml

team_name: edge-mac
table_name: edge_mac_bugs

queries:
  # SLA Bugs
  blocking:
    query_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    bug_type: "Blocking"
  a11y:
    query_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    bug_type: "A11y"
  security:
    query_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    bug_type: "Security"

  # High Priority
  need_triage:
    query_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    bug_type: "NeedTriage"
  p0p1:
    query_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    bug_type: "P0P1"
```

## MySQL 表结构

每个 Team 一张表，结构相同：

```sql
CREATE TABLE edge_mac_bugs (
    -- 主键
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,

    -- 基本信息
    bug_id INT NOT NULL,
    title VARCHAR(500) NOT NULL,
    state VARCHAR(50) NOT NULL,           -- New/Active/Resolved/Closed
    assigned_to VARCHAR(200),
    priority INT,                          -- 0/1/2/3
    severity VARCHAR(50),                  -- 1-Critical/2-High/3-Medium/4-Low

    -- 分类信息
    bug_type VARCHAR(50) NOT NULL,         -- Blocking/A11y/Security/NeedTriage/P0P1
    area_path VARCHAR(500),

    -- SLA 和时间
    sla_deadline DATE,
    created_date DATETIME,
    resolved_date DATETIME,
    closed_date DATETIME,

    -- 元数据
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- 唯一约束
    UNIQUE KEY uk_snapshot_bug_type (snapshot_date, bug_id, bug_type),

    -- 索引
    INDEX idx_snapshot_date (snapshot_date),
    INDEX idx_bug_id (bug_id),
    INDEX idx_bug_type (bug_type),
    INDEX idx_assigned_to (assigned_to)
);
```

**设计说明**：
- `snapshot_date` 记录快照日期，支持趋势分析
- 唯一键 `(snapshot_date, bug_id, bug_type)` 防止重复写入
- 同一个 bug 可能有多个 `bug_type`（比如既是 Blocking 又是 P0P1）

## Pipeline 脚本流程

```python
# scripts/sync_bugs.py

"""
Pipeline 调用方式：
  python scripts/sync_bugs.py                    # 同步所有 teams
  python scripts/sync_bugs.py --team edge-mac    # 同步指定 team
"""

def main():
    1. 解析命令行参数 (--team 可选)
    2. 加载 config/teams/*.yaml 配置文件
    3. 对每个 team:
        a. 遍历 team 的所有 queries
        b. 执行 az boards query --id {query_id} --output json
        c. 校验字段（必填字段检查、类型转换）
        d. 写入对应 team 的表（INSERT ... ON DUPLICATE KEY UPDATE）
    4. 输出同步结果统计
```

### 字段校验规则

| 字段 | 是否必填 | 校验规则 |
|------|----------|----------|
| bug_id | 必填 | 整数 |
| title | 必填 | 字符串 |
| state | 必填 | 枚举值校验 (New/Active/Resolved/Closed) |
| assigned_to | 可选 | 截断到 200 字符 |
| priority | 可选 | 0-3 范围 |
| sla_deadline | 可选 | 日期格式校验 |
| created_date | 必填 | 日期时间格式 |

### 错误处理

- 单个 query 失败不影响其他 query
- 记录失败的 query 和原因，最后汇总输出
- 脚本返回非零退出码表示有错误

## 数据更新策略

- **快照模式**：每天保存一份完整快照
- **频率**：每天一次
- **写入方式**：`INSERT ... ON DUPLICATE KEY UPDATE`

---

*文档创建时间: 2026-02-23*



  1. 配置真实的 Query ID - 替换 config/teams/*.yaml 中的占位符
  2. 设置 MySQL - 复制 .env.example 到 .env 并填入数据库信息
  3. 测试同步 - uv run python scripts/sync_bugs.py --dry-run
  4. 集成到 Pipeline - 在 ADO Pipeline 中调用脚本