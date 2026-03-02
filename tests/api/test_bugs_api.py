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
    assert "blocking_bugs" in data
    assert "overdue_bugs" in data
    assert "need_triage_bugs" in data


def test_get_teams_returns_200():
    """Test that /api/teams returns 200."""
    response = client.get("/api/teams")
    assert response.status_code == 200
    data = response.json()
    assert "teams" in data
    assert isinstance(data["teams"], list)


def test_get_team_summary_returns_200():
    """Test that /api/teams/{team_name}/summary returns 200 for valid team."""
    # First get the list of teams
    teams_response = client.get("/api/teams")
    teams = teams_response.json()["teams"]

    if teams:
        # Use the first team
        team_name = teams[0]["team_name"]
        response = client.get(f"/api/teams/{team_name}/summary")
        assert response.status_code == 200
        data = response.json()
        assert "team_name" in data
        assert "total_bugs" in data
        assert "sla_pass_rate" in data
        assert "overdue" in data
        assert "has_deadline" in data
        assert "by_type" in data
        assert "top_assignees" in data


def test_get_team_summary_returns_404_for_invalid_team():
    """Test that /api/teams/{team_name}/summary returns 404 for invalid team."""
    response = client.get("/api/teams/nonexistent-team/summary")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_get_team_bugs_returns_200():
    """Test that /api/teams/{team_name}/bugs returns 200 for valid team."""
    # First get the list of teams
    teams_response = client.get("/api/teams")
    teams = teams_response.json()["teams"]

    if teams:
        # Use the first team
        team_name = teams[0]["team_name"]
        response = client.get(f"/api/teams/{team_name}/bugs")
        assert response.status_code == 200
        data = response.json()
        assert "bugs" in data
        assert "total" in data
        assert isinstance(data["bugs"], list)


def test_get_team_bugs_with_filters():
    """Test that /api/teams/{team_name}/bugs supports query parameters."""
    # First get the list of teams
    teams_response = client.get("/api/teams")
    teams = teams_response.json()["teams"]

    if teams:
        # Use the first team
        team_name = teams[0]["team_name"]

        # Test with bug_type filter
        response = client.get(f"/api/teams/{team_name}/bugs?bug_type=Blocking")
        assert response.status_code == 200

        # Test with status filter
        response = client.get(f"/api/teams/{team_name}/bugs?status=overdue")
        assert response.status_code == 200

        # Test with search
        response = client.get(f"/api/teams/{team_name}/bugs?search=test")
        assert response.status_code == 200

        # Test with sort
        response = client.get(f"/api/teams/{team_name}/bugs?sort_by=priority&sort_order=desc")
        assert response.status_code == 200


def test_get_team_bugs_returns_404_for_invalid_team():
    """Test that /api/teams/{team_name}/bugs returns 404 for invalid team."""
    response = client.get("/api/teams/nonexistent-team/bugs")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_get_team_trend_returns_200():
    """Test that /api/teams/{team_name}/trend returns 200 for valid team."""
    # First get the list of teams
    teams_response = client.get("/api/teams")
    teams = teams_response.json()["teams"]

    if teams:
        # Use the first team
        team_name = teams[0]["team_name"]
        response = client.get(f"/api/teams/{team_name}/trend")
        assert response.status_code == 200
        data = response.json()
        assert "dates" in data
        assert "total" in data
        assert "blocking" in data
        assert "p0p1" in data
        assert isinstance(data["dates"], list)


def test_get_team_trend_with_days_parameter():
    """Test that /api/teams/{team_name}/trend supports days parameter."""
    # First get the list of teams
    teams_response = client.get("/api/teams")
    teams = teams_response.json()["teams"]

    if teams:
        # Use the first team
        team_name = teams[0]["team_name"]
        response = client.get(f"/api/teams/{team_name}/trend?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "dates" in data


def test_get_team_trend_returns_404_for_invalid_team():
    """Test that /api/teams/{team_name}/trend returns 404 for invalid team."""
    response = client.get("/api/teams/nonexistent-team/trend")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
