# Bug Status Dashboard Design

**Date**: 2026-02-24
**Status**: ✅ Implemented

## Overview

Build a web dashboard to display bug status data for Quality Push activities. The dashboard provides unified views of bugs across 3 teams (edge-mac, edge-mobile, edge-china-consumer) with 5 bug types (Blocking, A11y, Security, NeedTriage, P0P1).

### Use Cases
- **Daily review**: Quick overview of current bug status and trends
- **Meeting presentation**: Display on screen during Quality Push meetings

### Tech Stack
- **Backend**: FastAPI (Python)
- **Frontend**: HTML + Vanilla JS + CSS
- **Charts**: Chart.js
- **Styling**: Terminal/GitHub Dark theme (matching existing reference)

## Architecture

### Approach: FastAPI Static Files + Frontend Fetch API

```
frontend/
├── index.html              # Home page (team list + global stats)
├── team.html               # Team detail page (reusable)
├── css/
│   └── style.css           # Terminal/GitHub Dark theme
└── js/
    ├── api.js              # API request wrapper
    ├── charts.js           # Chart.js rendering
    ├── table.js            # Table component (sort, filter, pagination)
    └── app.js              # Main entry, page initialization

app/
├── api/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       └── bugs.py         # Bug API endpoints
└── main.py                 # FastAPI app entry
```

### Page Routes
- `/` → `index.html` (team list + global overview)
- `/team.html?team=edge-mac` → Team detail page

## Page Designs

### Home Page (index.html)

```
┌─────────────────────────────────────────────────────────────┐
│  Quality Push Dashboard                                      │
├─────────────────────────────────────────────────────────────┤
│  GLOBAL SUMMARY                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Total    │ │ Blocking │ │ Overdue  │ │ Need     │       │
│  │ Bugs     │ │ Bugs     │ │ SLA      │ │ Triage   │       │
│  │   611    │ │    115   │ │    23    │ │   313    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│  TEAM OVERVIEW                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Team              │ Total │ Blocking │ P0P1 │ Overdue │ │
│  ├───────────────────┼───────┼──────────┼──────┼─────────┤ │
│  │ edge-china-cons.. │  166  │    14    │  40  │    5    │ │
│  │ edge-mac          │   23  │     2    │  12  │    1    │ │
│  │ edge-mobile       │  422  │    99    │ 102  │   17    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                        [View Details →]     │
├─────────────────────────────────────────────────────────────┤
│  30-DAY TREND (All Teams)                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         [Chart.js line chart - bug count over time]    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Summary Cards:**
| Card | Data | Description |
|------|------|-------------|
| Total Bugs | Count of all active bugs | All teams combined |
| Blocking Bugs | Count of Blocking type | Red highlight |
| Overdue SLA | Bugs past due_date | Needs attention |
| Need Triage | NeedTriage type count | Waiting for triage |

**Team Table:**
- One row per team
- Columns: Team, Total, Blocking, P0P1, Overdue
- Click row to navigate to team detail page

**Trend Chart:**
- 30-day line chart showing total bug count
- Requires historical snapshot data

### Team Detail Page (team.html)

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back    Edge China Consumer - Bug Status Dashboard        │
├─────────────────────────────────────────────────────────────┤
│  SUMMARY STATISTICS                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Total    │ │ SLA Pass │ │ Overdue  │ │ Has      │       │
│  │ Bugs     │ │ Rate     │ │          │ │ Deadline │       │
│  │   166    │ │   85%    │ │    5     │ │   142    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│  BUG TYPE DISTRIBUTION                                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Blocking  ████████░░░░░░░░░░░░  14 (8%)               │ │
│  │ A11y      ░░░░░░░░░░░░░░░░░░░░   0 (0%)               │ │
│  │ Security  ███░░░░░░░░░░░░░░░░░   6 (4%)               │ │
│  │ NeedTriage████████████████████ 106 (64%)              │ │
│  │ P0P1      ████████████░░░░░░░░  40 (24%)              │ │
│  └────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │ 30-DAY TREND        │  │ TOP ASSIGNEES       │          │
│  │ [Chart.js line]     │  │ 1. Kun Wang    (12) │          │
│  │                     │  │ 2. Zhengyi Xu  (8)  │          │
│  │                     │  │ 3. Yang Huangfu(6)  │          │
│  └─────────────────────┘  └─────────────────────┘          │
├─────────────────────────────────────────────────────────────┤
│  BUG DETAILS                                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ [Type ▼] [Status ▼] [Search...        ]                │ │
│  ├──────┬─────────────────────┬────────┬─────────┬───────┤ │
│  │ ID   │ Title               │ Type   │ Due Date│Assignee│ │
│  ├──────┼─────────────────────┼────────┼─────────┼───────┤ │
│  │60319 │ [MSRC] Edge - Spoof │Blocking│ 05-21   │Kun W. │ │
│  │ ...  │                     │        │         │       │ │
│  └──────┴─────────────────────┴────────┴─────────┴───────┘ │
│  Showing 1-20 of 166    [< 1 2 3 4 5 ... 9 >]              │
└─────────────────────────────────────────────────────────────┘
```

**Table Columns:**
| Column | Source | Notes |
|--------|--------|-------|
| ID | bug_id | Clickable, links to ADO |
| Title | title | Truncated, hover for full |
| Type | bug_type | Blocking/A11y/Security/NeedTriage/P0P1 |
| Priority | priority | P0/P1/P2/P3/P4 |
| Due Date | due_date | Red=overdue, Yellow=within 7 days |
| Assignee | assigned_to | Display name |
| State | state | Active/Resolved/Closed |

**Table Features:**
| Feature | Implementation |
|---------|----------------|
| Type filter | Dropdown select bug_type |
| Status filter | Overdue / Due This Week / On Track |
| Search | Fuzzy match bug_id or title |
| Sort | Click header (ID, Due Date, Priority) |
| Pagination | 20 per page, client-side |

## API Design

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/summary` | GET | Global stats (all teams) |
| `/api/teams` | GET | Team list with summaries |
| `/api/teams/{team}/summary` | GET | Single team stats |
| `/api/teams/{team}/bugs` | GET | Bug list (with filters) |
| `/api/teams/{team}/trend` | GET | 30-day trend data |

### Response Formats

**GET /api/summary**
```json
{
  "total_bugs": 611,
  "blocking_bugs": 115,
  "overdue_bugs": 23,
  "need_triage_bugs": 313,
  "snapshot_date": "2026-02-24"
}
```

**GET /api/teams**
```json
{
  "teams": [
    {
      "team_name": "edge-china-consumer",
      "display_name": "Edge China Consumer",
      "total": 166,
      "blocking": 14,
      "p0p1": 40,
      "overdue": 5
    }
  ]
}
```

**GET /api/teams/{team}/summary**
```json
{
  "team_name": "edge-china-consumer",
  "total_bugs": 166,
  "sla_pass_rate": 85.5,
  "overdue": 5,
  "has_deadline": 142,
  "by_type": {
    "Blocking": 14,
    "A11y": 0,
    "Security": 6,
    "NeedTriage": 106,
    "P0P1": 40
  },
  "top_assignees": [
    {"name": "Kun Wang", "count": 12},
    {"name": "Zhengyi Xu", "count": 8}
  ]
}
```

**GET /api/teams/{team}/bugs**

Query parameters:
- `bug_type`: Filter by type (optional)
- `status`: overdue / this_week / on_track (optional)
- `search`: Search keyword (optional)
- `sort_by`: id / due_date / priority (default: due_date)
- `sort_order`: asc / desc (default: asc)

```json
{
  "bugs": [
    {
      "bug_id": 60319541,
      "title": "[MSRC] Edge - Spoofing...",
      "bug_type": "Blocking",
      "state": "Active",
      "priority": 1,
      "severity": "1",
      "assigned_to": "Kun Wang",
      "due_date": "2026-05-21",
      "created_date": "2025-11-23",
      "area_path": "Edge\\Consumer\\Core...",
      "ado_url": "https://microsoft.visualstudio.com/Edge/_workitems/edit/60319541"
    }
  ],
  "total": 166,
  "snapshot_date": "2026-02-24"
}
```

**GET /api/teams/{team}/trend**
```json
{
  "dates": ["2026-01-25", "2026-01-26", "...", "2026-02-24"],
  "total": [150, 152, 148, "...", 166],
  "blocking": [10, 11, 12, "...", 14],
  "p0p1": [35, 36, 38, "...", 40]
}
```

**Error Response**
```json
{
  "error": "Team not found",
  "detail": "No configuration found for team: invalid-team"
}
```

## Implementation Notes

### Data Source
- All data comes from MySQL tables created by sync_bugs.py
- Each team has its own table (e.g., `edge_china_consumer_bugs`)
- Trend data requires multiple days of snapshots

### ADO URL Format
```
https://microsoft.visualstudio.com/Edge/_workitems/edit/{bug_id}
```

### SLA Pass Rate Calculation
```
sla_pass_rate = (bugs_with_due_date - overdue_bugs) / bugs_with_due_date * 100
```

### Overdue Definition
```sql
WHERE due_date IS NOT NULL AND due_date < CURRENT_DATE AND state = 'Active'
```

## Next Steps

~~1. Implement FastAPI backend with API endpoints~~
~~2. Create frontend HTML/CSS/JS files~~
~~3. Integrate Chart.js for trend visualization~~
~~4. Test with real data~~

All steps completed. Dashboard is fully functional.

## Implementation Notes (Post-Implementation)

### Additional Features Added

Beyond the original design, the following features were implemented:

1. **Sidebar Navigation**: Fixed sidebar with team list for easy team switching
2. **5 Separate Bug Tables**: Instead of one filtered table, each bug type has its own table section
3. **ADO Query Links**: Table headers link directly to ADO queries
4. **Pie Charts**: Added distribution charts for Assignee and Area Path
5. **Leader Line Labels**: Custom Chart.js plugin for pie chart outer labels
6. **Compact Table Layout**: Fixed column widths with ellipsis for long titles
7. **Title Tooltips**: Hover to see full title text
8. **Area Path Formatting**: Shows only last 2 path segments
9. **Empty State**: Shows "Congratulations!!!" when bug list is empty

### Team Page Final Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  SIDEBAR  │  Terminal Window                                        │
│  ─────────│─────────────────────────────────────────────────────────│
│  Overview │  edge@quality-push ~/dashboard $ ./show_team_status.py   │
│           │                                                          │
│  Teams    │  BUG STATISTICS (5 cards)                               │
│  ├ Mac    │  ┌─────────┬─────────┬─────────┬─────────┬─────────┐   │
│  ├ Mobile │  │Blocking │  A11y   │Security │NeedTriage│ P0/P1   │   │
│  └ China  │  │   14    │    0    │    6    │   106   │   40    │   │
│           │  └─────────┴─────────┴─────────┴─────────┴─────────┘   │
│           │                                                          │
│           │  30-DAY TREND (5 colored lines in terminal body)        │
│           │  ┌──────────────────────────────────────────────────┐   │
│           │  │ Chart: Blocking, A11y, Security, NeedTriage, P0P1 │   │
│           │  └──────────────────────────────────────────────────┘   │
│           │                                                          │
│           │  BUG DISTRIBUTION (3-column layout)                     │
│           │  ┌────────────┬────────────┬────────────┐               │
│           │  │ By Assignee│By Area Path│Top Assignees│              │
│           │  │ (Pie Chart)│ (Pie Chart)│   (List)    │              │
│           │  └────────────┴────────────┴────────────┘               │
│           │                                                          │
│           │  BLOCKING BUGS (table with ADO link header)             │
│           │  A11Y BUGS (table with ADO link header)                 │
│           │  SECURITY BUGS (table with ADO link header)             │
│           │  NEED TRIAGE BUGS (table with ADO link header)          │
│           │  P0/P1 BUGS (table with ADO link header)                │
└───────────┴──────────────────────────────────────────────────────────┘
```
