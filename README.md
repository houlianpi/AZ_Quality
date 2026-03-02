# Quality Push Dashboard

Bug 状态看板，用于 Edge 团队的 Quality Push 活动。

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# MySQL 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=          # 你的 MySQL 密码（空密码则留空）
MYSQL_DATABASE=quality_platform

# AAD 认证（从 Azure Portal 获取）
AAD_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AAD_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**获取 AAD 配置：**
1. 打开 https://portal.azure.com
2. 进入 Microsoft Entra ID → App registrations
3. 找到或创建你的应用
4. 复制 Application (client) ID 和 Directory (tenant) ID
5. 在 Authentication 中添加 `http://localhost:8000` 作为 SPA Redirect URI

### 3. 创建数据库

```bash
mysql -u root -p
```

```sql
CREATE DATABASE quality_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 同步 Bug 数据

首次运行会自动创建表结构：

```bash
# 同步所有团队的数据
uv run python scripts/sync_bugs.py

# 只同步特定团队
uv run python scripts/sync_bugs.py --team edge-china-consumer

# 试运行（不写入数据库）
uv run python scripts/sync_bugs.py --dry-run
```

**注意：** 同步需要登录 Azure CLI (`az login`) 并有 ADO 查询权限。

### 5. 启动服务

```bash
uv run uvicorn app.main:app --reload --port 8000
```

打开浏览器访问：http://localhost:8000

## 功能

- **首页**：全局统计、团队列表、30天趋势图
- **团队页**：Bug 分类统计、趋势图、饼图、Bug 详情表格
- **认证**：Microsoft AAD 登录
- **数据**：每日快照，支持趋势分析

## 团队配置

团队配置文件在 `config/teams/` 目录：

```yaml
team_name: edge-china-consumer
table_name: edge_china_consumer_bugs

queries:
  blocking:
    query_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    bug_type: "Blocking"
  a11y:
    query_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    bug_type: "A11y"
  # ...
```

## 常用命令

```bash
# 启动服务（开发模式）
uv run uvicorn app.main:app --reload --port 8000

# 同步数据
uv run python scripts/sync_bugs.py

# 运行测试
uv run pytest

# 代码检查
uv run ruff check app/ scripts/
```

## 项目结构

```
quality_platform/
├── app/                    # FastAPI 后端
│   ├── api/routes/         # API 路由
│   ├── core/               # 配置、认证、数据库
│   ├── models/             # 数据模型
│   └── services/           # 业务逻辑
├── frontend/               # 前端静态文件
│   ├── js/                 # JavaScript 模块
│   ├── css/                # 样式
│   └── *.html              # 页面
├── scripts/                # 数据同步脚本
├── config/teams/           # 团队配置
└── docs/plans/             # 设计文档
```
