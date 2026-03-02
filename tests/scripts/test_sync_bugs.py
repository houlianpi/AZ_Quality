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
