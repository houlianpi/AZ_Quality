# tests/services/test_bug_service.py
from datetime import date

import pytest

from app.services.bug_service import BugService


def test_get_team_summary_returns_correct_structure():
    """Test that team summary returns expected fields."""
    service = BugService()

    # Get a valid team name from the service
    team_names = service.get_team_names()
    if not team_names:
        pytest.skip("No teams configured")

    team_name = team_names[0]
    summary = service.get_team_summary(team_name)

    assert "team_name" in summary
    assert "total_bugs" in summary
    assert "by_type" in summary
    assert "overdue" in summary
    assert "sla_pass_rate" in summary
    assert "has_deadline" in summary
    assert "top_assignees" in summary
    assert "snapshot_date" in summary

    assert summary["team_name"] == team_name
    assert isinstance(summary["total_bugs"], int)
    assert isinstance(summary["by_type"], dict)
    assert isinstance(summary["top_assignees"], list)


def test_get_global_summary_returns_correct_structure():
    """Test that global summary returns expected fields."""
    service = BugService()
    summary = service.get_global_summary()

    assert "total_bugs" in summary
    assert "blocking_bugs" in summary
    assert "overdue_bugs" in summary
    assert "need_triage_bugs" in summary
    assert "snapshot_date" in summary

    assert isinstance(summary["total_bugs"], int)
    assert isinstance(summary["blocking_bugs"], int)
    assert isinstance(summary["overdue_bugs"], int)


def test_get_team_names_returns_list():
    """Test that get_team_names returns a list of strings."""
    service = BugService()
    team_names = service.get_team_names()

    assert isinstance(team_names, list)
    # Should have at least the teams from config
    if team_names:
        assert all(isinstance(name, str) for name in team_names)


def test_get_team_config_returns_config():
    """Test that get_team_config returns config or None."""
    service = BugService()
    team_names = service.get_team_names()

    if team_names:
        config = service.get_team_config(team_names[0])
        assert config is not None
        assert hasattr(config, "team_name")
        assert hasattr(config, "table_name")

    # Test non-existent team
    config = service.get_team_config("non-existent-team")
    assert config is None


def test_get_teams_overview_returns_list():
    """Test that get_teams_overview returns list with correct structure."""
    service = BugService()
    teams = service.get_teams_overview()

    assert isinstance(teams, list)

    if teams:
        team = teams[0]
        assert "team_name" in team
        assert "display_name" in team
        assert "total" in team
        assert "blocking" in team
        assert "p0p1" in team
        assert "overdue" in team


def test_get_team_bugs_returns_correct_structure():
    """Test that get_team_bugs returns expected structure."""
    service = BugService()
    team_names = service.get_team_names()

    if not team_names:
        pytest.skip("No teams configured")

    team_name = team_names[0]
    result = service.get_team_bugs(team_name)

    assert "bugs" in result
    assert "total" in result
    assert "snapshot_date" in result
    assert isinstance(result["bugs"], list)
    assert isinstance(result["total"], int)

    # Check bug structure if there are bugs
    if result["bugs"]:
        bug = result["bugs"][0]
        assert "bug_id" in bug
        assert "title" in bug
        assert "bug_type" in bug
        assert "state" in bug
        assert "ado_url" in bug
        # Verify ADO URL format
        assert bug["ado_url"].startswith("https://microsoft.visualstudio.com/Edge/_workitems/edit/")


def test_get_team_bugs_with_filters():
    """Test that get_team_bugs respects filters."""
    service = BugService()
    team_names = service.get_team_names()

    if not team_names:
        pytest.skip("No teams configured")

    team_name = team_names[0]

    # Test with bug_type filter
    result = service.get_team_bugs(team_name, bug_type="Blocking")
    assert "bugs" in result

    # Test with status filter
    result = service.get_team_bugs(team_name, status="overdue")
    assert "bugs" in result

    # Test with search filter
    result = service.get_team_bugs(team_name, search="test")
    assert "bugs" in result


def test_get_team_trend_returns_correct_structure():
    """Test that get_team_trend returns expected structure."""
    service = BugService()
    team_names = service.get_team_names()

    if not team_names:
        pytest.skip("No teams configured")

    team_name = team_names[0]
    trend = service.get_team_trend(team_name, days=7)

    assert "dates" in trend
    assert "total" in trend
    assert "blocking" in trend
    assert "p0p1" in trend
    assert isinstance(trend["dates"], list)
    assert isinstance(trend["total"], list)
    assert isinstance(trend["blocking"], list)
    assert isinstance(trend["p0p1"], list)

    # All arrays should have same length
    assert len(trend["dates"]) == len(trend["total"])
    assert len(trend["dates"]) == len(trend["blocking"])
    assert len(trend["dates"]) == len(trend["p0p1"])


def test_invalid_team_name_raises_error():
    """Test that invalid team name raises ValueError."""
    service = BugService()

    with pytest.raises(ValueError, match="Team not found"):
        service.get_team_summary("non-existent-team")

    with pytest.raises(ValueError, match="Team not found"):
        service.get_team_bugs("non-existent-team")

    with pytest.raises(ValueError, match="Team not found"):
        service.get_team_trend("non-existent-team")


def test_sla_pass_rate_calculation():
    """Test that SLA pass rate is calculated correctly."""
    service = BugService()
    team_names = service.get_team_names()

    if not team_names:
        pytest.skip("No teams configured")

    team_name = team_names[0]
    summary = service.get_team_summary(team_name)

    # SLA pass rate should be between 0 and 100
    assert 0 <= summary["sla_pass_rate"] <= 100

    # If has_deadline is 0, sla_pass_rate should be 0
    if summary["has_deadline"] == 0:
        assert summary["sla_pass_rate"] == 0
    else:
        # Manual calculation: (has_deadline - overdue) / has_deadline * 100
        expected_rate = round(
            (summary["has_deadline"] - summary["overdue"]) / summary["has_deadline"] * 100,
            1
        )
        assert summary["sla_pass_rate"] == expected_rate
