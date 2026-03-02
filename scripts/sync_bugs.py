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

from app.core.database import SessionLocal, engine
from app.core.team_config import TeamConfig, load_all_team_configs
from app.models.bug import create_bug_table_class
from app.services.validator import ValidationError, validate_bug_record


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
        "az",
        "boards",
        "query",
        "--id",
        query_id,
        "--output",
        "json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise AzQueryError(f"az query failed: {result.stderr}")

    # Handle empty result (query returns no bugs)
    if not result.stdout.strip():
        return []

    try:
        parsed_data: list[dict[str, Any]] = json.loads(result.stdout)
        return parsed_data
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
    all_warnings: list[str] = []

    # Process each query
    for query_name, query_config in config.queries.items():
        try:
            print(f"  Running query: {query_name} ({query_config.bug_type})")
            raw_bugs = run_az_query(query_config.query_id)
            print(f"    Found {len(raw_bugs)} bugs")

            for raw_bug in raw_bugs:
                try:
                    validated, warnings = validate_bug_record(
                        raw_bug,
                        bug_type=query_config.bug_type,
                        snapshot_date=snapshot_date,
                        field_mapping=config.field_mapping,
                        required_fields=config.required_fields,
                    )
                    all_validated_bugs.append(validated)
                    all_warnings.extend(warnings)
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
        BugTable.metadata.create_all(engine, checkfirst=True)

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
                    tags=bug_data["tags"],
                    blocking=bug_data["blocking"],
                    release=bug_data["release"],
                    sdl_severity=bug_data["sdl_severity"],
                    due_date=bug_data["due_date"],
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
        print("Error: No team configs found" + (f" for team '{args.team}'" if args.team else ""))
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
