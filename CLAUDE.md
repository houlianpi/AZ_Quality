# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Quality Platform** is a web platform that integrates Azure DevOps (ADO) data for quality management activities. It provides unified views of bugs, test cases, and test tasks that are currently scattered across different ADO dashboards and queries.

**Target users**: ~50+ people including Quality team members, developers, team leads, and bug owners across 3 teams (edge-mobile, edge-mac, edge-china-consumer).

## Requirements

Full requirements are documented in `Doc/quality-platform-requirements.md` (in Chinese). Key points:

### Core Features (MVP Priority)
- **Quality Push Review**: SLA Bug Review, Bug Triage Queue, OCV/DSAT Review
- **New Feature Quality Tracking**: Feature→Task→Sub-task hierarchy, status distribution, progress trends
- **Test Execution Tracking**: Test plan progress, Pass/Fail/Blocked/Not Run statistics

### Technical Requirements
- **Data refresh**: Every 8 hours with local caching
- **Authentication**: ADO/AAD-based login for personalized views
- **Notifications**: Email (daily/weekly) + Teams Channel (real-time alerts)
- **Deployment**: Cloud-based

### Data Sources
- ADO Work Items (bugs, tasks, features)
- ADO Test Plans (manual tests)
- ADO Pipelines (automated tests)
- Experiment Platform/ECS (Phase 3, API TBD)

## Tech Stack

- **Backend**: Python 3.11+ with FastAPI
- **Package Manager**: uv
- **Database**: MySQL (data caching layer)
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic 2.0
- **Auth**: msal (Microsoft AAD authentication)
- **Data sync**: Pipeline executes `az boards query`, writes to MySQL

## Project Structure

```
quality_platform/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── bugs.py       # Bug API endpoints (protected)
│   ├── core/
│   │   ├── auth.py           # AAD JWT verification
│   │   ├── config.py         # Settings via pydantic-settings
│   │   ├── database.py       # MySQL connection (engine, SessionLocal)
│   │   └── team_config.py    # Team YAML config loader
│   ├── models/
│   │   └── bug.py            # Bug SQLAlchemy model + dynamic table factory
│   ├── services/
│   │   ├── validator.py      # ADO JSON → DB record validation
│   │   └── bug_service.py    # Bug query service layer
│   └── main.py               # FastAPI app entry point
├── frontend/
│   ├── index.html            # Home page (global stats + team list)
│   ├── team.html             # Team detail page
│   ├── css/
│   │   └── style.css         # Terminal/GitHub Dark theme
│   └── js/
│       ├── auth.js           # MSAL.js AAD authentication
│       ├── api.js            # API request wrapper (with auth token)
│       ├── charts.js         # Chart.js rendering (trend + pie charts)
│       ├── table.js          # Table component (sort, filter, pagination)
│       └── app.js            # Main entry, page initialization
├── scripts/
│   ├── sync_bugs.py          # Pipeline script: az query → MySQL
│   └── check_query_fields.py # Utility: Check ADO Query field configuration
├── config/
│   └── teams/
│       ├── edge_mac.yaml
│       ├── edge_mobile.yaml
│       └── edge_china_consumer.yaml
├── tests/
│   ├── core/
│   │   ├── test_config.py
│   │   └── test_team_config.py
│   ├── models/
│   │   └── test_bug.py
│   ├── services/
│   │   └── test_validator.py
│   └── scripts/
│       └── test_sync_bugs.py
├── docs/
│   └── plans/                # Design and implementation plans
├── .env.example
├── pyproject.toml
└── CLAUDE.md
```

## Development Commands

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov=scripts --cov-report=term-missing

# Run single test
uv run pytest tests/core/test_config.py::test_settings_loads_from_env -v

# Type checking
uv run mypy app/ scripts/

# Linting
uv run ruff check app/ scripts/

# Format code
uv run ruff format app/ scripts/
```

## Bug Status Dashboard

```bash
# Start the dashboard server
uv run uvicorn app.main:app --reload --port 8000

# Open in browser
open http://localhost:8000
```

**Features:**
- **Home page** (`/`): Global stats, team overview table, 30-day trend chart
- **Team page** (`/team.html?team=<name>`): Team stats, trend chart, pie charts, bug tables

**Frontend Stack:**
- HTML + Vanilla JS + CSS
- Chart.js for trend and pie chart visualization
- Terminal/GitHub Dark theme

**API Endpoints:**
| Endpoint | Description |
|----------|-------------|
| `/api/summary` | Global stats (all teams) |
| `/api/teams` | Team list with summaries |
| `/api/teams/{team}/summary` | Single team stats |
| `/api/teams/{team}/bugs` | Bug list (with filters) |
| `/api/teams/{team}/trend` | 30-day trend data |
| `/api/teams/{team}/query-links` | ADO query links |
| `/api/me` | Current authenticated user info |
| `/api/auth/config` | AAD config for frontend (public) |

## AAD Authentication

All API endpoints (except `/api/auth/config`) require Microsoft AAD authentication.

**Setup:**
1. Register an app in Azure Portal → Microsoft Entra ID → App registrations
2. Add `http://localhost:8000` as SPA Redirect URI
3. Configure `.env` with your AAD credentials:

```bash
AAD_CLIENT_ID=your-client-id
AAD_TENANT_ID=your-tenant-id
```

**How it works:**
- Frontend uses MSAL.js for login popup
- ID Token stored in sessionStorage
- All API requests include `Authorization: Bearer <token>`
- Backend verifies JWT signature against AAD public keys

**Files:**
- `frontend/js/auth.js` - MSAL.js authentication module
- `app/core/auth.py` - JWT verification and FastAPI dependency

## Pipeline Sync Script

```bash
# Sync all teams (production)
uv run python scripts/sync_bugs.py

# Sync specific team
uv run python scripts/sync_bugs.py --team edge-china-consumer

# Dry run (validate without writing to DB)
uv run python scripts/sync_bugs.py --dry-run

# Specify snapshot date
uv run python scripts/sync_bugs.py --date 2026-02-23

# Show help
uv run python scripts/sync_bugs.py --help

# Check ADO Query field configuration
uv run python scripts/check_query_fields.py
```

## Team Configuration

Each team has a YAML config file in `config/teams/`:

```yaml
team_name: edge-mac
table_name: edge_mac_bugs

queries:
  blocking:
    query_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    bug_type: "Blocking"
  a11y:
    query_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    bug_type: "A11y"
  # ... more queries

# Optional: Custom field mapping for non-standard ADO fields
field_mapping:
  sdl_severity: "OSG.SDLSeverity"  # Custom SDL Severity field

# Optional: Configure required vs warn-if-missing fields
# Uses ADO Column display names (e.g., "Assigned To") or internal names (e.g., "assigned_to")
required_fields:
  required:
    - ID
    - Title
    - State
    - Assigned To
    - Area Path
    - Created Date
  warn_if_missing:
    - Due Date
    - Priority
    - Severity
    - Blocking
    - Release
    - Tags
    - SDL Severity
```

**Bug types**: Blocking, A11y, Security, NeedTriage, P0P1

### Field Mapping

The system supports configurable field mapping from ADO field names to database columns:

| ADO Column Name | Internal Field | Database Column |
|-----------------|----------------|-----------------|
| ID | bug_id | bug_id |
| Title | title | title |
| State | state | state |
| Assigned To | assigned_to | assigned_to |
| Priority | priority | priority |
| Severity | severity | severity |
| Area Path | area_path | area_path |
| Created Date | created_date | created_date |
| Due Date | due_date | due_date |
| Tags | tags | tags |
| Blocking | blocking | blocking |
| Release | release | release |
| SDL Severity | sdl_severity | sdl_severity |

Custom fields (like `OSG.SDLSeverity`) can be mapped via `field_mapping` in the team config.

## Key Patterns

### Data Flow
```
ADO → az boards query → sync_bugs.py → validate → MySQL (per-team tables)
```

### Database Schema
- Each team has its own table (e.g., `edge_mac_bugs`, `edge_china_consumer_bugs`)
- Daily snapshots with `snapshot_date` field for trend analysis
- Unique constraint on `(snapshot_date, bug_id, bug_type)`

### Bug Table Columns
```
bug_id, snapshot_date, bug_type, title, state, assigned_to,
priority, severity, area_path, created_date, resolved_date, closed_date,
tags, due_date, blocking, release, sdl_severity, synced_at
```

### Dynamic Table Factory
```python
from app.models.bug import create_bug_table_class

EdgeMacBug = create_bug_table_class("edge_mac_bugs")
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# MySQL Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=quality_platform

# AAD Authentication
AAD_CLIENT_ID=your-client-id
AAD_TENANT_ID=your-tenant-id
```

## Alert Thresholds (Defaults)
- SLA advance notice: 7 days
- Feature completion warning: 80%
- Feature stagnation: 15 days without progress
