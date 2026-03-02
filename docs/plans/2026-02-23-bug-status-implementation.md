# Bug Status 数据存储实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Bug Status 模块的数据存储层，包括数据库模型、配置加载、字段校验和 Pipeline 同步脚本。

**Architecture:** Pipeline 脚本读取 Team 配置文件，执行 `az boards query` 获取 ADO Bug 数据，校验后写入 MySQL。每个 Team 一张表，每天一个快照。

**Tech Stack:** Python 3.11+, uv, SQLAlchemy 2.0, PyYAML, MySQL, pytest

---

## Task 1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/core/__init__.py`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`
- Create: `config/teams/.gitkeep`

**Step 1: 初始化 uv 项目**

```bash
uv init --name quality-platform
```

**Step 2: 替换 pyproject.toml 内容**

```toml
[project]
name = "quality-platform"
version = "0.1.0"
description = "Quality Platform for Edge team"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "sqlalchemy>=2.0.0",
    "pymysql>=1.1.0",
    "pyyaml>=6.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
    "types-PyYAML>=6.0.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

**Step 3: 创建目录结构**

```bash
mkdir -p app/core app/models scripts tests config/teams
touch app/__init__.py app/core/__init__.py app/models/__init__.py scripts/__init__.py tests/__init__.py config/teams/.gitkeep
```

**Step 4: 安装依赖**

```bash
uv sync
```

Expected: 依赖安装成功，生成 `uv.lock` 文件

**Step 5: 验证项目结构**

```bash
ls -la app/ scripts/ tests/ config/teams/
```

**Step 6: Commit**

```bash
git add pyproject.toml uv.lock app/ scripts/ tests/ config/
git commit -m "chore: initialize project structure with uv

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 数据库配置模块

**Files:**
- Create: `app/core/config.py`
- Create: `app/core/database.py`
- Create: `tests/core/__init__.py`
- Create: `tests/core/test_config.py`

**Step 1: 写配置测试**

```python
# tests/core/test_config.py
import os
from unittest.mock import patch


def test_settings_loads_from_env():
    """Test that Settings loads database config from environment variables."""
    env_vars = {
        "MYSQL_HOST": "testhost",
        "MYSQL_PORT": "3307",
        "MYSQL_USER": "testuser",
        "MYSQL_PASSWORD": "testpass",
        "MYSQL_DATABASE": "testdb",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        # Import inside to pick up patched env
        from app.core.config import Settings
        settings = Settings()

        assert settings.MYSQL_HOST == "testhost"
        assert settings.MYSQL_PORT == 3307
        assert settings.MYSQL_USER == "testuser"
        assert settings.MYSQL_PASSWORD == "testpass"
        assert settings.MYSQL_DATABASE == "testdb"


def test_settings_database_url():
    """Test that database_url property returns correct MySQL URL."""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "root",
        "MYSQL_PASSWORD": "secret",
        "MYSQL_DATABASE": "quality_platform",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        from app.core.config import Settings
        settings = Settings()

        expected = "mysql+pymysql://root:secret@localhost:3306/quality_platform"
        assert settings.database_url == expected
```

**Step 2: 运行测试，确认失败**

```bash
mkdir -p tests/core && touch tests/core/__init__.py
uv run pytest tests/core/test_config.py -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'app.core.config'`

**Step 3: 实现配置模块**

```python
# app/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "quality_platform"

    @property
    def database_url(self) -> str:
        """Return MySQL connection URL for SQLAlchemy."""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
```

**Step 4: 运行测试，确认通过**

```bash
uv run pytest tests/core/test_config.py -v
```

Expected: PASS

**Step 5: 实现数据库连接模块**

```python
# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 6: Commit**

```bash
git add app/core/config.py app/core/database.py tests/core/
git commit -m "feat: add database configuration module

- Settings class with MySQL connection parameters
- Database engine and session factory
- Tests for config loading

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Bug 数据模型

**Files:**
- Create: `app/models/bug.py`
- Create: `tests/models/__init__.py`
- Create: `tests/models/test_bug.py`

**Step 1: 写模型测试**

```python
# tests/models/test_bug.py
from datetime import date, datetime

from app.models.bug import BugRecord


def test_bug_record_creation():
    """Test BugRecord model can be instantiated with all fields."""
    bug = BugRecord(
        snapshot_date=date(2026, 2, 23),
        bug_id=12345,
        title="Test bug title",
        state="Active",
        assigned_to="user@example.com",
        priority=1,
        severity="2-High",
        bug_type="Blocking",
        area_path="Edge\\Mobile",
        sla_deadline=date(2026, 3, 1),
        created_date=datetime(2026, 2, 20, 10, 30, 0),
        resolved_date=None,
        closed_date=None,
    )

    assert bug.bug_id == 12345
    assert bug.title == "Test bug title"
    assert bug.state == "Active"
    assert bug.bug_type == "Blocking"


def test_bug_record_table_name_factory():
    """Test that create_bug_table_class creates table with correct name."""
    from app.models.bug import create_bug_table_class

    EdgeMacBug = create_bug_table_class("edge_mac_bugs")
    assert EdgeMacBug.__tablename__ == "edge_mac_bugs"

    EdgeMobileBug = create_bug_table_class("edge_mobile_bugs")
    assert EdgeMobileBug.__tablename__ == "edge_mobile_bugs"
```

**Step 2: 运行测试，确认失败**

```bash
mkdir -p tests/models && touch tests/models/__init__.py
uv run pytest tests/models/test_bug.py -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'app.models.bug'`

**Step 3: 实现 Bug 模型**

```python
# app/models/bug.py
from datetime import date, datetime
from typing import Optional, Type

from sqlalchemy import Date, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BugRecord(Base):
    """
    Base Bug record model. Use create_bug_table_class() to create
    team-specific table classes.
    """
    __tablename__ = "bugs"  # Default, overridden by factory
    __abstract__ = True  # Don't create this table directly

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Basic info
    bug_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    priority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Classification
    bug_type: Mapped[str] = mapped_column(String(50), nullable=False)
    area_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # SLA and dates
    sla_deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Metadata
    synced_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


# Cache for dynamically created table classes
_table_class_cache: dict[str, Type[BugRecord]] = {}


def create_bug_table_class(table_name: str) -> Type[BugRecord]:
    """
    Factory function to create a BugRecord subclass with specific table name.

    Args:
        table_name: The MySQL table name (e.g., 'edge_mac_bugs')

    Returns:
        A new class that maps to the specified table
    """
    if table_name in _table_class_cache:
        return _table_class_cache[table_name]

    class_name = "".join(word.capitalize() for word in table_name.split("_"))

    new_class = type(
        class_name,
        (Base,),
        {
            "__tablename__": table_name,
            "__table_args__": (
                UniqueConstraint(
                    "snapshot_date", "bug_id", "bug_type",
                    name=f"uk_{table_name}_snapshot_bug_type"
                ),
                Index(f"idx_{table_name}_snapshot_date", "snapshot_date"),
                Index(f"idx_{table_name}_bug_id", "bug_id"),
                Index(f"idx_{table_name}_bug_type", "bug_type"),
                Index(f"idx_{table_name}_assigned_to", "assigned_to"),
            ),
            # Copy all columns from BugRecord
            "id": mapped_column(Integer, primary_key=True, autoincrement=True),
            "snapshot_date": mapped_column(Date, nullable=False),
            "bug_id": mapped_column(Integer, nullable=False),
            "title": mapped_column(String(500), nullable=False),
            "state": mapped_column(String(50), nullable=False),
            "assigned_to": mapped_column(String(200), nullable=True),
            "priority": mapped_column(Integer, nullable=True),
            "severity": mapped_column(String(50), nullable=True),
            "bug_type": mapped_column(String(50), nullable=False),
            "area_path": mapped_column(String(500), nullable=True),
            "sla_deadline": mapped_column(Date, nullable=True),
            "created_date": mapped_column(DateTime, nullable=True),
            "resolved_date": mapped_column(DateTime, nullable=True),
            "closed_date": mapped_column(DateTime, nullable=True),
            "synced_at": mapped_column(DateTime, nullable=False, default=datetime.utcnow),
        }
    )

    _table_class_cache[table_name] = new_class
    return new_class
```

**Step 4: 运行测试，确认通过**

```bash
uv run pytest tests/models/test_bug.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/models/bug.py tests/models/
git commit -m "feat: add Bug data model with dynamic table factory

- BugRecord base model with all required fields
- create_bug_table_class() factory for team-specific tables
- Unique constraint on (snapshot_date, bug_id, bug_type)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Team 配置加载器

**Files:**
- Create: `app/core/team_config.py`
- Create: `tests/core/test_team_config.py`
- Create: `config/teams/edge_mac.yaml` (示例)

**Step 1: 写配置加载测试**

```python
# tests/core/test_team_config.py
import tempfile
from pathlib import Path

import pytest
import yaml

from app.core.team_config import TeamConfig, load_team_config, load_all_team_configs


def test_team_config_from_yaml():
    """Test TeamConfig can be loaded from YAML dict."""
    data = {
        "team_name": "edge-mac",
        "table_name": "edge_mac_bugs",
        "queries": {
            "blocking": {
                "query_id": "abc-123",
                "bug_type": "Blocking"
            }
        }
    }
    config = TeamConfig.model_validate(data)

    assert config.team_name == "edge-mac"
    assert config.table_name == "edge_mac_bugs"
    assert len(config.queries) == 1
    assert config.queries["blocking"].query_id == "abc-123"
    assert config.queries["blocking"].bug_type == "Blocking"


def test_load_team_config_from_file():
    """Test loading TeamConfig from a YAML file."""
    yaml_content = """
team_name: edge-mobile
table_name: edge_mobile_bugs
queries:
  blocking:
    query_id: "def-456"
    bug_type: "Blocking"
  a11y:
    query_id: "ghi-789"
    bug_type: "A11y"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        config = load_team_config(Path(f.name))

        assert config.team_name == "edge-mobile"
        assert len(config.queries) == 2


def test_load_all_team_configs():
    """Test loading all team configs from a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two config files
        for team in ["edge_mac", "edge_mobile"]:
            yaml_content = f"""
team_name: {team.replace("_", "-")}
table_name: {team}_bugs
queries:
  blocking:
    query_id: "query-{team}"
    bug_type: "Blocking"
"""
            with open(Path(tmpdir) / f"{team}.yaml", "w") as f:
                f.write(yaml_content)

        configs = load_all_team_configs(Path(tmpdir))

        assert len(configs) == 2
        team_names = {c.team_name for c in configs}
        assert team_names == {"edge-mac", "edge-mobile"}
```

**Step 2: 运行测试，确认失败**

```bash
uv run pytest tests/core/test_team_config.py -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'app.core.team_config'`

**Step 3: 实现配置加载器**

```python
# app/core/team_config.py
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class QueryConfig(BaseModel):
    """Configuration for a single ADO query."""
    query_id: str
    bug_type: str


class TeamConfig(BaseModel):
    """Configuration for a team's bug sync."""
    team_name: str
    table_name: str
    queries: dict[str, QueryConfig]


def load_team_config(config_path: Path) -> TeamConfig:
    """
    Load a team configuration from a YAML file.

    Args:
        config_path: Path to the YAML config file

    Returns:
        TeamConfig object

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is invalid
        pydantic.ValidationError: If config structure is invalid
    """
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return TeamConfig.model_validate(data)


def load_all_team_configs(
    config_dir: Path,
    team_filter: Optional[str] = None
) -> list[TeamConfig]:
    """
    Load all team configurations from a directory.

    Args:
        config_dir: Directory containing YAML config files
        team_filter: Optional team name to filter (loads only that team)

    Returns:
        List of TeamConfig objects
    """
    configs = []

    for yaml_file in sorted(config_dir.glob("*.yaml")):
        config = load_team_config(yaml_file)

        if team_filter is None or config.team_name == team_filter:
            configs.append(config)

    return configs
```

**Step 4: 运行测试，确认通过**

```bash
uv run pytest tests/core/test_team_config.py -v
```

Expected: PASS

**Step 5: 创建示例配置文件**

```yaml
# config/teams/edge_mac.yaml
team_name: edge-mac
table_name: edge_mac_bugs

queries:
  blocking:
    query_id: "00000000-0000-0000-0000-000000000001"
    bug_type: "Blocking"
  a11y:
    query_id: "00000000-0000-0000-0000-000000000002"
    bug_type: "A11y"
  security:
    query_id: "00000000-0000-0000-0000-000000000003"
    bug_type: "Security"
  need_triage:
    query_id: "00000000-0000-0000-0000-000000000004"
    bug_type: "NeedTriage"
  p0p1:
    query_id: "00000000-0000-0000-0000-000000000005"
    bug_type: "P0P1"
```

**Step 6: Commit**

```bash
git add app/core/team_config.py tests/core/test_team_config.py config/teams/edge_mac.yaml
git commit -m "feat: add team configuration loader

- TeamConfig and QueryConfig Pydantic models
- YAML config loading with validation
- Example config for edge-mac team

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 字段校验器

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/validator.py`
- Create: `tests/services/__init__.py`
- Create: `tests/services/test_validator.py`

**Step 1: 写校验器测试**

```python
# tests/services/test_validator.py
from datetime import date, datetime

import pytest

from app.services.validator import (
    validate_bug_record,
    ValidationError,
    parse_ado_date,
)


def test_validate_bug_record_valid():
    """Test validation passes for valid bug data."""
    raw_data = {
        "id": 12345,
        "fields": {
            "System.Title": "Test bug",
            "System.State": "Active",
            "System.AssignedTo": {"displayName": "John Doe"},
            "Microsoft.VSTS.Common.Priority": 1,
            "Microsoft.VSTS.Common.Severity": "2 - High",
            "System.AreaPath": "Edge\\Mobile",
            "System.CreatedDate": "2026-02-20T10:30:00Z",
        }
    }

    result = validate_bug_record(raw_data, bug_type="Blocking", snapshot_date=date(2026, 2, 23))

    assert result["bug_id"] == 12345
    assert result["title"] == "Test bug"
    assert result["state"] == "Active"
    assert result["bug_type"] == "Blocking"
    assert result["snapshot_date"] == date(2026, 2, 23)


def test_validate_bug_record_missing_required_field():
    """Test validation fails when required field is missing."""
    raw_data = {
        "id": 12345,
        "fields": {
            # Missing System.Title
            "System.State": "Active",
            "System.CreatedDate": "2026-02-20T10:30:00Z",
        }
    }

    with pytest.raises(ValidationError) as exc_info:
        validate_bug_record(raw_data, bug_type="Blocking", snapshot_date=date(2026, 2, 23))

    assert "title" in str(exc_info.value).lower()


def test_validate_bug_record_truncates_long_assigned_to():
    """Test that assigned_to is truncated to 200 characters."""
    long_name = "A" * 300
    raw_data = {
        "id": 12345,
        "fields": {
            "System.Title": "Test bug",
            "System.State": "Active",
            "System.AssignedTo": {"displayName": long_name},
            "System.CreatedDate": "2026-02-20T10:30:00Z",
        }
    }

    result = validate_bug_record(raw_data, bug_type="Blocking", snapshot_date=date(2026, 2, 23))

    assert len(result["assigned_to"]) == 200


def test_parse_ado_date_iso_format():
    """Test parsing ADO date in ISO format."""
    result = parse_ado_date("2026-02-20T10:30:00Z")
    assert result == datetime(2026, 2, 20, 10, 30, 0)


def test_parse_ado_date_none():
    """Test parsing None returns None."""
    result = parse_ado_date(None)
    assert result is None
```

**Step 2: 运行测试，确认失败**

```bash
mkdir -p app/services tests/services
touch app/services/__init__.py tests/services/__init__.py
uv run pytest tests/services/test_validator.py -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'app.services.validator'`

**Step 3: 实现校验器**

```python
# app/services/validator.py
from datetime import date, datetime
from typing import Any, Optional


class ValidationError(Exception):
    """Raised when bug data validation fails."""
    pass


def parse_ado_date(value: Optional[str]) -> Optional[datetime]:
    """
    Parse an ADO date string to datetime.

    Args:
        value: Date string in ISO format (e.g., "2026-02-20T10:30:00Z")

    Returns:
        datetime object or None if value is None/empty
    """
    if not value:
        return None

    # Handle ISO format with Z suffix
    if value.endswith("Z"):
        value = value[:-1]

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def validate_bug_record(
    raw_data: dict[str, Any],
    bug_type: str,
    snapshot_date: date,
) -> dict[str, Any]:
    """
    Validate and transform raw ADO bug data into database record format.

    Args:
        raw_data: Raw JSON from az boards query
        bug_type: The bug classification type
        snapshot_date: The snapshot date for this sync

    Returns:
        Dict ready for database insertion

    Raises:
        ValidationError: If required fields are missing or invalid
    """
    fields = raw_data.get("fields", {})

    # Required fields
    bug_id = raw_data.get("id")
    if bug_id is None:
        raise ValidationError("Missing required field: id")

    title = fields.get("System.Title")
    if not title:
        raise ValidationError("Missing required field: title (System.Title)")

    state = fields.get("System.State")
    if not state:
        raise ValidationError("Missing required field: state (System.State)")

    # Optional fields with transformations
    assigned_to_data = fields.get("System.AssignedTo")
    assigned_to = None
    if assigned_to_data:
        if isinstance(assigned_to_data, dict):
            assigned_to = assigned_to_data.get("displayName", "")
        else:
            assigned_to = str(assigned_to_data)
        # Truncate to 200 characters
        if len(assigned_to) > 200:
            assigned_to = assigned_to[:200]

    priority = fields.get("Microsoft.VSTS.Common.Priority")
    if priority is not None:
        try:
            priority = int(priority)
            if priority < 0 or priority > 3:
                priority = None
        except (ValueError, TypeError):
            priority = None

    severity = fields.get("Microsoft.VSTS.Common.Severity")
    if severity and len(str(severity)) > 50:
        severity = str(severity)[:50]

    area_path = fields.get("System.AreaPath")
    if area_path and len(str(area_path)) > 500:
        area_path = str(area_path)[:500]

    # Date fields
    created_date = parse_ado_date(fields.get("System.CreatedDate"))
    resolved_date = parse_ado_date(fields.get("Microsoft.VSTS.Common.ResolvedDate"))
    closed_date = parse_ado_date(fields.get("Microsoft.VSTS.Common.ClosedDate"))

    # SLA deadline - might be in different fields depending on ADO config
    sla_deadline_str = fields.get("Custom.SLADeadline") or fields.get("Microsoft.VSTS.Scheduling.DueDate")
    sla_deadline = None
    if sla_deadline_str:
        parsed = parse_ado_date(sla_deadline_str)
        if parsed:
            sla_deadline = parsed.date()

    return {
        "snapshot_date": snapshot_date,
        "bug_id": bug_id,
        "title": str(title)[:500],
        "state": str(state)[:50],
        "assigned_to": assigned_to,
        "priority": priority,
        "severity": str(severity)[:50] if severity else None,
        "bug_type": bug_type,
        "area_path": area_path,
        "sla_deadline": sla_deadline,
        "created_date": created_date,
        "resolved_date": resolved_date,
        "closed_date": closed_date,
    }
```

**Step 4: 运行测试，确认通过**

```bash
uv run pytest tests/services/test_validator.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/services/ tests/services/
git commit -m "feat: add bug record validator

- validate_bug_record() transforms ADO JSON to DB format
- Field truncation for long strings
- Date parsing for ADO ISO format
- ValidationError for missing required fields

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Pipeline 同步脚本

**Files:**
- Create: `scripts/sync_bugs.py`
- Create: `tests/scripts/__init__.py`
- Create: `tests/scripts/test_sync_bugs.py`

**Step 1: 写脚本测试（模拟 az 命令）**

```python
# tests/scripts/test_sync_bugs.py
import json
import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_run_az_query_success():
    """Test running az boards query successfully."""
    from scripts.sync_bugs import run_az_query

    mock_result = [
        {"id": 1, "fields": {"System.Title": "Bug 1", "System.State": "Active", "System.CreatedDate": "2026-02-20T00:00:00Z"}},
        {"id": 2, "fields": {"System.Title": "Bug 2", "System.State": "Resolved", "System.CreatedDate": "2026-02-20T00:00:00Z"}},
    ]

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_result),
            stderr=""
        )

        result = run_az_query("test-query-id")

        assert len(result) == 2
        assert result[0]["id"] == 1


def test_run_az_query_failure():
    """Test handling az command failure."""
    from scripts.sync_bugs import run_az_query, AzQueryError

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Query not found"
        )

        with pytest.raises(AzQueryError):
            run_az_query("invalid-query-id")


def test_sync_team_bugs_dry_run():
    """Test sync_team_bugs in dry-run mode (no DB writes)."""
    from scripts.sync_bugs import sync_team_bugs, SyncResult
    from app.core.team_config import TeamConfig, QueryConfig

    config = TeamConfig(
        team_name="test-team",
        table_name="test_bugs",
        queries={
            "blocking": QueryConfig(query_id="q1", bug_type="Blocking"),
        }
    )

    mock_bugs = [
        {"id": 1, "fields": {"System.Title": "Bug 1", "System.State": "Active", "System.CreatedDate": "2026-02-20T00:00:00Z"}},
    ]

    with patch("scripts.sync_bugs.run_az_query", return_value=mock_bugs):
        result = sync_team_bugs(config, snapshot_date=date(2026, 2, 23), dry_run=True)

        assert isinstance(result, SyncResult)
        assert result.team_name == "test-team"
        assert result.total_bugs == 1
        assert result.success
```

**Step 2: 运行测试，确认失败**

```bash
mkdir -p tests/scripts && touch tests/scripts/__init__.py
uv run pytest tests/scripts/test_sync_bugs.py -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'scripts.sync_bugs'`

**Step 3: 实现同步脚本**

```python
# scripts/sync_bugs.py
#!/usr/bin/env python3
"""
Pipeline script to sync bug data from ADO to MySQL.

Usage:
    python scripts/sync_bugs.py                    # Sync all teams
    python scripts/sync_bugs.py --team edge-mac    # Sync specific team
    python scripts/sync_bugs.py --dry-run          # Validate without writing
"""
import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.mysql import insert

from app.core.database import engine, SessionLocal
from app.core.team_config import TeamConfig, load_all_team_configs
from app.models.bug import create_bug_table_class
from app.services.validator import validate_bug_record, ValidationError


class AzQueryError(Exception):
    """Raised when az boards query fails."""
    pass


@dataclass
class SyncResult:
    """Result of syncing bugs for a team."""
    team_name: str
    success: bool = True
    total_bugs: int = 0
    inserted: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)


def run_az_query(query_id: str) -> list[dict[str, Any]]:
    """
    Execute az boards query and return results.

    Args:
        query_id: The ADO query GUID

    Returns:
        List of work items from the query

    Raises:
        AzQueryError: If the az command fails
    """
    cmd = [
        "az", "boards", "query",
        "--id", query_id,
        "--output", "json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise AzQueryError(f"az query failed: {result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AzQueryError(f"Invalid JSON from az command: {e}")


def sync_team_bugs(
    config: TeamConfig,
    snapshot_date: date,
    dry_run: bool = False,
) -> SyncResult:
    """
    Sync all bugs for a team.

    Args:
        config: Team configuration
        snapshot_date: The date for this snapshot
        dry_run: If True, validate only without writing to DB

    Returns:
        SyncResult with statistics
    """
    result = SyncResult(team_name=config.team_name)
    all_validated_bugs: list[dict[str, Any]] = []

    # Process each query
    for query_name, query_config in config.queries.items():
        try:
            print(f"  Running query: {query_name} ({query_config.bug_type})")
            raw_bugs = run_az_query(query_config.query_id)
            print(f"    Found {len(raw_bugs)} bugs")

            for raw_bug in raw_bugs:
                try:
                    validated = validate_bug_record(
                        raw_bug,
                        bug_type=query_config.bug_type,
                        snapshot_date=snapshot_date,
                    )
                    all_validated_bugs.append(validated)
                except ValidationError as e:
                    bug_id = raw_bug.get("id", "unknown")
                    result.errors.append(f"Bug {bug_id}: {e}")

        except AzQueryError as e:
            result.errors.append(f"Query {query_name}: {e}")
            result.success = False

    result.total_bugs = len(all_validated_bugs)

    if dry_run:
        print(f"  [DRY RUN] Would insert/update {result.total_bugs} bugs")
        return result

    # Write to database
    if all_validated_bugs:
        BugTable = create_bug_table_class(config.table_name)

        # Ensure table exists
        BugTable.__table__.create(engine, checkfirst=True)

        with SessionLocal() as session:
            for bug_data in all_validated_bugs:
                stmt = insert(BugTable).values(**bug_data)
                stmt = stmt.on_duplicate_key_update(
                    title=bug_data["title"],
                    state=bug_data["state"],
                    assigned_to=bug_data["assigned_to"],
                    priority=bug_data["priority"],
                    severity=bug_data["severity"],
                    area_path=bug_data["area_path"],
                    sla_deadline=bug_data["sla_deadline"],
                    resolved_date=bug_data["resolved_date"],
                    closed_date=bug_data["closed_date"],
                    synced_at=text("CURRENT_TIMESTAMP"),
                )
                session.execute(stmt)

            session.commit()
            result.inserted = len(all_validated_bugs)  # Simplified counting

    return result


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sync bug data from ADO to MySQL")
    parser.add_argument("--team", help="Sync only this team (e.g., edge-mac)")
    parser.add_argument("--config-dir", default="config/teams", help="Config directory")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    parser.add_argument("--date", help="Snapshot date (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    # Determine snapshot date
    if args.date:
        snapshot_date = date.fromisoformat(args.date)
    else:
        snapshot_date = date.today()

    print(f"Snapshot date: {snapshot_date}")
    print(f"Config directory: {args.config_dir}")
    if args.dry_run:
        print("DRY RUN MODE - no database writes")
    print()

    # Load configs
    config_dir = Path(args.config_dir)
    if not config_dir.exists():
        print(f"Error: Config directory not found: {config_dir}")
        return 1

    configs = load_all_team_configs(config_dir, team_filter=args.team)

    if not configs:
        print(f"Error: No team configs found" + (f" for team '{args.team}'" if args.team else ""))
        return 1

    print(f"Found {len(configs)} team(s) to sync")
    print()

    # Sync each team
    all_results: list[SyncResult] = []

    for config in configs:
        print(f"Syncing team: {config.team_name}")
        result = sync_team_bugs(config, snapshot_date, dry_run=args.dry_run)
        all_results.append(result)

        if result.errors:
            print(f"  Errors: {len(result.errors)}")
            for err in result.errors[:5]:  # Show first 5 errors
                print(f"    - {err}")

        print(f"  Total bugs: {result.total_bugs}")
        print()

    # Summary
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)

    total_bugs = sum(r.total_bugs for r in all_results)
    total_errors = sum(len(r.errors) for r in all_results)
    failed_teams = [r for r in all_results if not r.success]

    print(f"Teams processed: {len(all_results)}")
    print(f"Total bugs: {total_bugs}")
    print(f"Total errors: {total_errors}")

    if failed_teams:
        print(f"Failed teams: {', '.join(r.team_name for r in failed_teams)}")
        return 1

    print("All teams synced successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: 运行测试，确认通过**

```bash
uv run pytest tests/scripts/test_sync_bugs.py -v
```

Expected: PASS

**Step 5: 测试脚本 help**

```bash
uv run python scripts/sync_bugs.py --help
```

Expected: 显示帮助信息

**Step 6: Commit**

```bash
git add scripts/sync_bugs.py tests/scripts/
git commit -m "feat: add pipeline sync script

- run_az_query() executes az boards query
- sync_team_bugs() processes all queries for a team
- Support for --team, --dry-run, --date flags
- Error handling and summary statistics

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: 添加更多 Team 配置

**Files:**
- Create: `config/teams/edge_mobile.yaml`
- Create: `config/teams/edge_china_consumer.yaml`

**Step 1: 创建 edge_mobile 配置**

```yaml
# config/teams/edge_mobile.yaml
team_name: edge-mobile
table_name: edge_mobile_bugs

queries:
  blocking:
    query_id: "00000000-0000-0000-0000-000000000011"
    bug_type: "Blocking"
  a11y:
    query_id: "00000000-0000-0000-0000-000000000012"
    bug_type: "A11y"
  security:
    query_id: "00000000-0000-0000-0000-000000000013"
    bug_type: "Security"
  need_triage:
    query_id: "00000000-0000-0000-0000-000000000014"
    bug_type: "NeedTriage"
  p0p1:
    query_id: "00000000-0000-0000-0000-000000000015"
    bug_type: "P0P1"
```

**Step 2: 创建 edge_china_consumer 配置**

```yaml
# config/teams/edge_china_consumer.yaml
team_name: edge-china-consumer
table_name: edge_china_consumer_bugs

queries:
  blocking:
    query_id: "00000000-0000-0000-0000-000000000021"
    bug_type: "Blocking"
  a11y:
    query_id: "00000000-0000-0000-0000-000000000022"
    bug_type: "A11y"
  security:
    query_id: "00000000-0000-0000-0000-000000000023"
    bug_type: "Security"
  need_triage:
    query_id: "00000000-0000-0000-0000-000000000024"
    bug_type: "NeedTriage"
  p0p1:
    query_id: "00000000-0000-0000-0000-000000000025"
    bug_type: "P0P1"
```

**Step 3: 验证配置可加载**

```bash
uv run python -c "
from pathlib import Path
from app.core.team_config import load_all_team_configs
configs = load_all_team_configs(Path('config/teams'))
for c in configs:
    print(f'{c.team_name}: {len(c.queries)} queries')
"
```

Expected:
```
edge-china-consumer: 5 queries
edge-mac: 5 queries
edge-mobile: 5 queries
```

**Step 4: Commit**

```bash
git add config/teams/
git commit -m "feat: add team configs for edge-mobile and edge-china-consumer

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: 运行完整测试套件

**Step 1: 运行所有测试**

```bash
uv run pytest --cov=app --cov=scripts --cov-report=term-missing
```

Expected: 所有测试通过，覆盖率报告显示

**Step 2: 运行类型检查**

```bash
uv run mypy app/ scripts/
```

Expected: 无错误或仅有 minor warnings

**Step 3: 运行 linter**

```bash
uv run ruff check app/ scripts/
uv run ruff format --check app/ scripts/
```

Expected: 无错误

**Step 4: 修复任何问题后 Commit**

```bash
git add -A
git commit -m "chore: fix linting and type issues

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: 创建 .env.example

**Files:**
- Create: `.env.example`

**Step 1: 创建环境变量示例文件**

```bash
# .env.example
# Copy this file to .env and fill in your values

# MySQL Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=quality_platform
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add .env.example

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 完成检查清单

- [ ] Task 1: 项目初始化 (uv, pyproject.toml)
- [ ] Task 2: 数据库配置模块
- [ ] Task 3: Bug 数据模型
- [ ] Task 4: Team 配置加载器
- [ ] Task 5: 字段校验器
- [ ] Task 6: Pipeline 同步脚本
- [ ] Task 7: 添加更多 Team 配置
- [ ] Task 8: 运行完整测试套件
- [ ] Task 9: 创建 .env.example

---

*计划创建时间: 2026-02-23*
