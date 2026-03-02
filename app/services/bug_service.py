# app/services/bug_service.py
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func
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

    def _format_area_path(self, area_path: str) -> str:
        """Format area path to show only last 2 segments."""
        if not area_path:
            return "Unknown"
        parts = area_path.split("\\")
        if len(parts) <= 2:
            return area_path
        return "\\".join(parts[-2:])

    def get_team_query_links(self, team_name: str) -> dict[str, str]:
        """
        Get ADO query links for a team.

        Args:
            team_name: Team name

        Returns:
            Dictionary mapping bug type to ADO query URL
        """
        config = self._configs.get(team_name)
        if not config:
            raise ValueError(f"Team not found: {team_name}")

        base_url = "https://microsoft.visualstudio.com/Edge/_queries/query"
        query_links = {}

        for query_key, query_config in config.queries.items():
            bug_type = query_config.bug_type.lower()
            query_links[bug_type] = f"{base_url}/{query_config.query_id}"

        return query_links

    def _get_latest_snapshot_date(self, session: Session, table_name: str) -> date | None:
        """Get the most recent snapshot date for a team."""
        BugTable = create_bug_table_class(table_name)
        result = session.query(func.max(BugTable.snapshot_date)).scalar()
        return result

    def get_team_summary(self, team_name: str) -> dict[str, Any]:
        """
        Get summary statistics for a team.

        Returns:
            Dictionary with:
            - team_name: Team name
            - total_bugs: Total number of bugs
            - sla_pass_rate: SLA pass rate percentage
            - overdue: Number of overdue bugs
            - has_deadline: Number of bugs with deadlines
            - by_type: Bug count by type
            - top_assignees: Top 10 assignees with bug counts
            - snapshot_date: Latest snapshot date
        """
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

            # Top area paths
            top_area_paths_raw = (
                session.query(BugTable.area_path, func.count(BugTable.id))
                .filter(
                    BugTable.snapshot_date == snapshot_date,
                    BugTable.area_path.isnot(None),
                )
                .group_by(BugTable.area_path)
                .order_by(func.count(BugTable.id).desc())
                .limit(10)
                .all()
            )
            top_area_paths = [
                {"name": self._format_area_path(path), "count": count}
                for path, count in top_area_paths_raw
            ]

            return {
                "team_name": team_name,
                "total_bugs": total,
                "sla_pass_rate": sla_pass_rate,
                "overdue": overdue,
                "has_deadline": has_deadline,
                "by_type": by_type,
                "top_assignees": top_assignees,
                "top_area_paths": top_area_paths,
                "snapshot_date": snapshot_date.isoformat(),
            }

    def get_global_summary(self) -> dict[str, Any]:
        """
        Get summary statistics across all teams.

        Returns:
            Dictionary with:
            - total_bugs: Total bugs across all teams
            - blocking_bugs: Total blocking bugs
            - overdue_bugs: Total overdue bugs
            - need_triage_bugs: Total bugs needing triage
            - snapshot_date: Latest snapshot date
        """
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
        """
        Get overview of all teams with summary stats.

        Returns:
            List of dictionaries with:
            - team_name: Team name
            - display_name: Formatted display name
            - total: Total bugs
            - blocking: Blocking bugs
            - p0p1: P0/P1 bugs
            - overdue: Overdue bugs
        """
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
        """
        Get bug list for a team with filters.

        Args:
            team_name: Team name
            bug_type: Filter by bug type (optional)
            status: Filter by status: "overdue", "this_week", "on_track" (optional)
            search: Search in title or bug_id (optional)
            sort_by: Column to sort by (default: "due_date")
            sort_order: Sort order: "asc" or "desc" (default: "asc")

        Returns:
            Dictionary with:
            - bugs: List of bug dictionaries with ADO URL
            - total: Total count
            - snapshot_date: Snapshot date
        """
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

            # Sort - MySQL doesn't support NULLS LAST, use CASE to put NULLs last
            sort_column = getattr(BugTable, sort_by, BugTable.due_date)
            # Create a CASE expression to handle NULLs: put NULLs last
            if sort_order == "desc":
                # For DESC: non-NULL DESC, then NULL
                from sqlalchemy import case
                query = query.order_by(
                    case((sort_column.is_(None), 1), else_=0),
                    sort_column.desc()
                )
            else:
                # For ASC: non-NULL ASC, then NULL
                from sqlalchemy import case
                query = query.order_by(
                    case((sort_column.is_(None), 1), else_=0),
                    sort_column.asc()
                )

            # Execute
            bugs = query.all()
            total = len(bugs)

            # Convert to dict with ADO URL
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
        """
        Get trend data for the past N days.

        Args:
            team_name: Team name
            days: Number of days to look back (default: 30)

        Returns:
            Dictionary with:
            - dates: List of date strings
            - blocking: List of Blocking bug counts per date
            - a11y: List of A11y bug counts per date
            - security: List of Security bug counts per date
            - needtriage: List of NeedTriage bug counts per date
            - p0p1: List of P0P1 bug counts per date
        """
        config = self._configs.get(team_name)
        if not config:
            raise ValueError(f"Team not found: {team_name}")

        BugTable = create_bug_table_class(config.table_name)

        with SessionLocal() as session:
            # Get unique snapshot dates
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

            # Organize by date with all 5 bug types
            date_data: dict[str, dict[str, int]] = {}
            bug_types = ["Blocking", "A11y", "Security", "NeedTriage", "P0P1"]

            for snap_date, bug_type, count in results:
                date_str = snap_date.isoformat()
                if date_str not in date_data:
                    date_data[date_str] = {t: 0 for t in bug_types}
                if bug_type in bug_types:
                    date_data[date_str][bug_type] = count

            # Convert to arrays
            dates = sorted(date_data.keys())

            return {
                "dates": dates,
                "blocking": [date_data[d]["Blocking"] for d in dates],
                "a11y": [date_data[d]["A11y"] for d in dates],
                "security": [date_data[d]["Security"] for d in dates],
                "needtriage": [date_data[d]["NeedTriage"] for d in dates],
                "p0p1": [date_data[d]["P0P1"] for d in dates],
            }
