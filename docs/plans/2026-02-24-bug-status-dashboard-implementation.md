# Bug Status Dashboard Implementation Plan

> **Status**: ✅ COMPLETED (2026-02-24)

**Goal:** Build a web dashboard displaying bug status data with FastAPI backend and HTML/JS frontend.

**Architecture:** FastAPI serves static files + REST API endpoints. Frontend uses vanilla JS with Chart.js. Terminal/GitHub Dark theme matching existing reference.

**Tech Stack:** FastAPI, SQLAlchemy, HTML/CSS/JS, Chart.js

---

## Implementation Summary

All tasks completed successfully. The dashboard is fully functional with the following features:

### Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| FastAPI backend | ✅ | CORS, static files, API routes |
| Bug Service Layer | ✅ | Team summary, bugs list, trend data |
| API Endpoints | ✅ | 6 endpoints including query-links |
| Home Page | ✅ | Global stats, team table, trend chart |
| Team Page | ✅ | 5 bug type stats, charts, 5 bug tables |
| Sidebar Navigation | ✅ | Dynamic team list, collapsible |
| Trend Chart | ✅ | 5 colored lines for bug types |
| Pie Charts | ✅ | By Assignee + By Area Path with leader lines |
| Bug Tables | ✅ | Sort, filter, search, pagination, ADO links |

### Final File Structure

```
frontend/
├── index.html              # Home page
├── team.html               # Team detail page
├── css/
│   └── style.css           # Terminal/GitHub Dark theme (scanlines, cursor)
└── js/
    ├── api.js              # API request wrapper
    ├── charts.js           # Chart.js (trend lines + pie with outer labels)
    ├── table.js            # Table component with multi-table support
    └── app.js              # Page initialization, sidebar loading

app/
├── main.py                 # FastAPI entry point
├── api/
│   └── routes/
│       └── bugs.py         # 6 API endpoints
└── services/
    └── bug_service.py      # Query service with query links
```

### API Endpoints Implemented

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/summary` | GET | Global stats (all teams) |
| `/api/teams` | GET | Team list with summaries |
| `/api/teams/{team}/summary` | GET | Team stats + top assignees + area paths |
| `/api/teams/{team}/bugs` | GET | Bug list with filters |
| `/api/teams/{team}/trend` | GET | 30-day trend (5 bug types) |
| `/api/teams/{team}/query-links` | GET | ADO query URLs for each bug type |

### Key Implementation Decisions

1. **Dynamic table class factory**: Added `extend_existing=True` to prevent SQLAlchemy table redefinition errors
2. **MySQL NULL handling**: Used `CASE` expression instead of `NULLS LAST` for sort ordering
3. **Pie chart labels**: Custom Chart.js plugin draws leader lines and external labels for slices ≥3%
4. **Table layout**: Used `table-layout: fixed` with specific column widths for consistent spacing
5. **Area path formatting**: Shows only last 2 segments for readability

---

## Original Task Plan (Reference)

## Task 1: FastAPI App Entry Point

**Files:**
- Create: `app/main.py`
- Create: `app/api/__init__.py`
- Create: `app/api/routes/__init__.py`

**Step 1: Create FastAPI main.py**

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import bugs

app = FastAPI(
    title="Quality Platform API",
    description="Bug status dashboard API",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(bugs.router, prefix="/api", tags=["bugs"])

# Static files (frontend)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

**Step 2: Create empty route module files**

```python
# app/api/__init__.py
# API package

# app/api/routes/__init__.py
# Routes package
```

**Step 3: Test server starts**

Run: `uv run uvicorn app.main:app --reload --port 8000`
Expected: Server starts, shows "Uvicorn running on http://127.0.0.1:8000"

**Step 4: Commit**

```bash
git add app/main.py app/api/__init__.py app/api/routes/__init__.py
git commit -m "feat: add FastAPI app entry point with CORS and static files"
```

---

## Task 2: Bug Service Layer

**Files:**
- Create: `app/services/bug_service.py`
- Test: `tests/services/test_bug_service.py`

**Step 1: Write the failing test**

```python
# tests/services/test_bug_service.py
from datetime import date

import pytest

from app.services.bug_service import BugService


def test_get_team_summary_returns_correct_structure():
    """Test that team summary returns expected fields."""
    service = BugService()
    # This will fail because BugService doesn't exist yet
    summary = service.get_team_summary("edge-china-consumer")

    assert "team_name" in summary
    assert "total_bugs" in summary
    assert "by_type" in summary


def test_get_global_summary_returns_correct_structure():
    """Test that global summary returns expected fields."""
    service = BugService()
    summary = service.get_global_summary()

    assert "total_bugs" in summary
    assert "blocking_bugs" in summary
    assert "overdue_bugs" in summary
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_bug_service.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.bug_service'"

**Step 3: Write the bug service implementation**

```python
# app/services/bug_service.py
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.team_config import TeamConfig, load_all_team_configs
from app.models.bug import create_bug_table_class


class BugService:
    """Service for querying bug data from MySQL."""

    def __init__(self, config_dir: Path = Path("config/teams")):
        self.config_dir = config_dir
        self._configs: dict[str, TeamConfig] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """Load all team configurations."""
        configs = load_all_team_configs(self.config_dir)
        for config in configs:
            self._configs[config.team_name] = config

    def get_team_names(self) -> list[str]:
        """Get list of all team names."""
        return list(self._configs.keys())

    def get_team_config(self, team_name: str) -> TeamConfig | None:
        """Get configuration for a specific team."""
        return self._configs.get(team_name)

    def _get_latest_snapshot_date(self, session: Session, table_name: str) -> date | None:
        """Get the most recent snapshot date for a team."""
        BugTable = create_bug_table_class(table_name)
        result = session.query(func.max(BugTable.snapshot_date)).scalar()
        return result

    def get_team_summary(self, team_name: str) -> dict[str, Any]:
        """Get summary statistics for a team."""
        config = self._configs.get(team_name)
        if not config:
            raise ValueError(f"Team not found: {team_name}")

        BugTable = create_bug_table_class(config.table_name)
        today = date.today()

        with SessionLocal() as session:
            snapshot_date = self._get_latest_snapshot_date(session, config.table_name)
            if not snapshot_date:
                return {
                    "team_name": team_name,
                    "total_bugs": 0,
                    "sla_pass_rate": 0,
                    "overdue": 0,
                    "has_deadline": 0,
                    "by_type": {},
                    "top_assignees": [],
                    "snapshot_date": None,
                }

            # Base query for latest snapshot
            base_query = session.query(BugTable).filter(
                BugTable.snapshot_date == snapshot_date
            )

            # Total bugs
            total = base_query.count()

            # By type
            by_type = {}
            type_counts = (
                session.query(BugTable.bug_type, func.count(BugTable.id))
                .filter(BugTable.snapshot_date == snapshot_date)
                .group_by(BugTable.bug_type)
                .all()
            )
            for bug_type, count in type_counts:
                by_type[bug_type] = count

            # Overdue (due_date < today and state = Active)
            overdue = (
                base_query.filter(
                    BugTable.due_date < today,
                    BugTable.state == "Active",
                )
                .count()
            )

            # Has deadline
            has_deadline = base_query.filter(BugTable.due_date.isnot(None)).count()

            # SLA pass rate
            sla_pass_rate = 0.0
            if has_deadline > 0:
                sla_pass_rate = round((has_deadline - overdue) / has_deadline * 100, 1)

            # Top assignees
            top_assignees_raw = (
                session.query(BugTable.assigned_to, func.count(BugTable.id))
                .filter(
                    BugTable.snapshot_date == snapshot_date,
                    BugTable.assigned_to.isnot(None),
                )
                .group_by(BugTable.assigned_to)
                .order_by(func.count(BugTable.id).desc())
                .limit(10)
                .all()
            )
            top_assignees = [
                {"name": name, "count": count}
                for name, count in top_assignees_raw
            ]

            return {
                "team_name": team_name,
                "total_bugs": total,
                "sla_pass_rate": sla_pass_rate,
                "overdue": overdue,
                "has_deadline": has_deadline,
                "by_type": by_type,
                "top_assignees": top_assignees,
                "snapshot_date": snapshot_date.isoformat(),
            }

    def get_global_summary(self) -> dict[str, Any]:
        """Get summary statistics across all teams."""
        total_bugs = 0
        blocking_bugs = 0
        overdue_bugs = 0
        need_triage_bugs = 0
        latest_snapshot = None

        for team_name in self._configs:
            summary = self.get_team_summary(team_name)
            total_bugs += summary["total_bugs"]
            blocking_bugs += summary["by_type"].get("Blocking", 0)
            overdue_bugs += summary["overdue"]
            need_triage_bugs += summary["by_type"].get("NeedTriage", 0)
            if summary["snapshot_date"]:
                if latest_snapshot is None or summary["snapshot_date"] > latest_snapshot:
                    latest_snapshot = summary["snapshot_date"]

        return {
            "total_bugs": total_bugs,
            "blocking_bugs": blocking_bugs,
            "overdue_bugs": overdue_bugs,
            "need_triage_bugs": need_triage_bugs,
            "snapshot_date": latest_snapshot,
        }

    def get_teams_overview(self) -> list[dict[str, Any]]:
        """Get overview of all teams with summary stats."""
        teams = []
        for team_name, config in self._configs.items():
            summary = self.get_team_summary(team_name)
            teams.append({
                "team_name": team_name,
                "display_name": team_name.replace("-", " ").title(),
                "total": summary["total_bugs"],
                "blocking": summary["by_type"].get("Blocking", 0),
                "p0p1": summary["by_type"].get("P0P1", 0),
                "overdue": summary["overdue"],
            })
        return teams

    def get_team_bugs(
        self,
        team_name: str,
        bug_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        sort_by: str = "due_date",
        sort_order: str = "asc",
    ) -> dict[str, Any]:
        """Get bug list for a team with filters."""
        config = self._configs.get(team_name)
        if not config:
            raise ValueError(f"Team not found: {team_name}")

        BugTable = create_bug_table_class(config.table_name)
        today = date.today()

        with SessionLocal() as session:
            snapshot_date = self._get_latest_snapshot_date(session, config.table_name)
            if not snapshot_date:
                return {"bugs": [], "total": 0, "snapshot_date": None}

            query = session.query(BugTable).filter(
                BugTable.snapshot_date == snapshot_date
            )

            # Filter by bug_type
            if bug_type:
                query = query.filter(BugTable.bug_type == bug_type)

            # Filter by status
            if status == "overdue":
                query = query.filter(
                    BugTable.due_date < today,
                    BugTable.state == "Active",
                )
            elif status == "this_week":
                from datetime import timedelta
                week_end = today + timedelta(days=7)
                query = query.filter(
                    BugTable.due_date >= today,
                    BugTable.due_date <= week_end,
                )
            elif status == "on_track":
                query = query.filter(
                    (BugTable.due_date >= today) | (BugTable.due_date.is_(None))
                )

            # Search
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (BugTable.title.like(search_pattern)) |
                    (BugTable.bug_id.like(search_pattern))
                )

            # Sort
            sort_column = getattr(BugTable, sort_by, BugTable.due_date)
            if sort_order == "desc":
                sort_column = sort_column.desc()
            query = query.order_by(sort_column.nulls_last())

            # Execute
            bugs = query.all()
            total = len(bugs)

            # Convert to dict
            bug_list = []
            for bug in bugs:
                bug_list.append({
                    "bug_id": bug.bug_id,
                    "title": bug.title,
                    "bug_type": bug.bug_type,
                    "state": bug.state,
                    "priority": bug.priority,
                    "severity": bug.severity,
                    "assigned_to": bug.assigned_to,
                    "due_date": bug.due_date.isoformat() if bug.due_date else None,
                    "created_date": bug.created_date.isoformat() if bug.created_date else None,
                    "area_path": bug.area_path,
                    "ado_url": f"https://microsoft.visualstudio.com/Edge/_workitems/edit/{bug.bug_id}",
                })

            return {
                "bugs": bug_list,
                "total": total,
                "snapshot_date": snapshot_date.isoformat(),
            }

    def get_team_trend(self, team_name: str, days: int = 30) -> dict[str, Any]:
        """Get trend data for the past N days."""
        config = self._configs.get(team_name)
        if not config:
            raise ValueError(f"Team not found: {team_name}")

        BugTable = create_bug_table_class(config.table_name)

        with SessionLocal() as session:
            # Get unique snapshot dates
            from datetime import timedelta
            cutoff = date.today() - timedelta(days=days)

            results = (
                session.query(
                    BugTable.snapshot_date,
                    BugTable.bug_type,
                    func.count(BugTable.id),
                )
                .filter(BugTable.snapshot_date >= cutoff)
                .group_by(BugTable.snapshot_date, BugTable.bug_type)
                .order_by(BugTable.snapshot_date)
                .all()
            )

            # Organize by date
            date_data: dict[str, dict[str, int]] = {}
            for snap_date, bug_type, count in results:
                date_str = snap_date.isoformat()
                if date_str not in date_data:
                    date_data[date_str] = {"total": 0, "Blocking": 0, "P0P1": 0}
                date_data[date_str]["total"] += count
                if bug_type in ["Blocking", "P0P1"]:
                    date_data[date_str][bug_type] = count

            # Convert to arrays
            dates = sorted(date_data.keys())
            total = [date_data[d]["total"] for d in dates]
            blocking = [date_data[d]["Blocking"] for d in dates]
            p0p1 = [date_data[d]["P0P1"] for d in dates]

            return {
                "dates": dates,
                "total": total,
                "blocking": blocking,
                "p0p1": p0p1,
            }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_bug_service.py -v`
Expected: PASS (tests may pass with empty data)

**Step 5: Commit**

```bash
git add app/services/bug_service.py tests/services/test_bug_service.py
git commit -m "feat: add BugService for querying bug data"
```

---

## Task 3: API Routes

**Files:**
- Create: `app/api/routes/bugs.py`
- Test: `tests/api/test_bugs_api.py`

**Step 1: Write the failing test**

```python
# tests/api/test_bugs_api.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_summary_returns_200():
    """Test that /api/summary returns 200."""
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_bugs" in data


def test_get_teams_returns_200():
    """Test that /api/teams returns 200."""
    response = client.get("/api/teams")
    assert response.status_code == 200
    data = response.json()
    assert "teams" in data
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_bugs_api.py -v`
Expected: FAIL with 404 (routes not implemented)

**Step 3: Implement API routes**

```python
# app/api/routes/bugs.py
from fastapi import APIRouter, HTTPException, Query

from app.services.bug_service import BugService

router = APIRouter()
bug_service = BugService()


@router.get("/summary")
def get_summary():
    """Get global summary across all teams."""
    return bug_service.get_global_summary()


@router.get("/teams")
def get_teams():
    """Get list of teams with summary stats."""
    teams = bug_service.get_teams_overview()
    return {"teams": teams}


@router.get("/teams/{team_name}/summary")
def get_team_summary(team_name: str):
    """Get summary for a specific team."""
    try:
        return bug_service.get_team_summary(team_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/teams/{team_name}/bugs")
def get_team_bugs(
    team_name: str,
    bug_type: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("due_date"),
    sort_order: str = Query("asc"),
):
    """Get bug list for a team with optional filters."""
    try:
        return bug_service.get_team_bugs(
            team_name,
            bug_type=bug_type,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/teams/{team_name}/trend")
def get_team_trend(team_name: str, days: int = Query(30)):
    """Get trend data for a team."""
    try:
        return bug_service.get_team_trend(team_name, days=days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/api/test_bugs_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/api/routes/bugs.py tests/api/test_bugs_api.py
git commit -m "feat: add bug API routes"
```

---

## Task 4: Frontend Structure (Use /frontend-design Skill)

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/team.html`
- Create: `frontend/css/style.css`
- Create: `frontend/js/api.js`
- Create: `frontend/js/charts.js`
- Create: `frontend/js/table.js`
- Create: `frontend/js/app.js`

**Step 1: Create frontend directory structure**

```bash
mkdir -p frontend/css frontend/js
```

**Step 2: Use /frontend-design skill**

Invoke the `/frontend-design` skill with the following prompt:

> Create a bug status dashboard with Terminal/GitHub Dark theme. Reference style from Doc/edge-mobile_sla_report_2026-02-11.html.
>
> **index.html**: Home page with:
> - Summary cards (Total Bugs, Blocking, Overdue, Need Triage)
> - Team overview table (Team, Total, Blocking, P0P1, Overdue) - clickable rows
> - 30-day trend chart using Chart.js
>
> **team.html**: Team detail page with:
> - Back button, team name header
> - Summary cards (Total, SLA Pass Rate, Overdue, Has Deadline)
> - Bug type distribution progress bars
> - 30-day trend chart + Top Assignees list
> - Bug table with: filters (Type, Status), search, sortable columns, pagination
>
> **JS modules**:
> - api.js: fetch wrapper for /api/* endpoints
> - charts.js: Chart.js line chart rendering
> - table.js: table with sort, filter, pagination
> - app.js: page initialization

**Step 3: Verify frontend loads**

Run: `uv run uvicorn app.main:app --reload --port 8000`
Open: http://localhost:8000
Expected: Dashboard page loads with dark theme

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add frontend dashboard pages"
```

---

## Task 5: Integration Test

**Files:**
- Test: `tests/integration/test_dashboard.py`

**Step 1: Write integration test**

```python
# tests/integration/test_dashboard.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_summary_matches_teams():
    """Test that global summary matches sum of team summaries."""
    summary = client.get("/api/summary").json()
    teams = client.get("/api/teams").json()["teams"]

    total_from_teams = sum(t["total"] for t in teams)
    assert summary["total_bugs"] == total_from_teams


def test_team_detail_page_loads():
    """Test that team detail page loads."""
    response = client.get("/team.html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_index_page_loads():
    """Test that index page loads."""
    response = client.get("/")
    assert response.status_code == 200
```

**Step 2: Run integration tests**

Run: `uv run pytest tests/integration/test_dashboard.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_dashboard.py
git commit -m "test: add dashboard integration tests"
```

---

## Task 6: Manual End-to-End Test

**Step 1: Start the server**

Run: `uv run uvicorn app.main:app --reload --port 8000`

**Step 2: Test API endpoints**

```bash
curl http://localhost:8000/api/summary
curl http://localhost:8000/api/teams
curl http://localhost:8000/api/teams/edge-china-consumer/summary
curl http://localhost:8000/api/teams/edge-china-consumer/bugs
curl http://localhost:8000/api/teams/edge-china-consumer/trend
```

**Step 3: Test frontend pages**

- Open http://localhost:8000 - verify summary cards and team table load
- Click on a team row - verify navigation to team detail page
- Verify charts render correctly
- Test table filters, search, sort, pagination

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete bug status dashboard v1.0"
```

---

## Summary

| Task | Description | Status |
|------|-------------|--------|
| 1 | FastAPI App Entry Point | ✅ Completed |
| 2 | Bug Service Layer | ✅ Completed |
| 3 | API Routes | ✅ Completed |
| 4 | Frontend Structure (/frontend-design) | ✅ Completed |
| 5 | Integration Tests | ✅ Completed |
| 6 | Manual E2E Test | ✅ Completed |

### Additional Features (Post-MVP)

| Feature | Description | Status |
|---------|-------------|--------|
| Sidebar Navigation | Fixed sidebar with team list | ✅ Added |
| 5 Bug Tables | Separate tables per bug type | ✅ Added |
| ADO Query Links | Clickable table titles → ADO | ✅ Added |
| Pie Charts | Assignee + Area Path distribution | ✅ Added |
| Outer Labels | Leader lines for pie chart labels | ✅ Added |
| Compact Tables | Fixed column widths, ellipsis titles | ✅ Added |
| Empty State | "Congratulations!!!" when no bugs | ✅ Added |
