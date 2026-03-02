"""Integration tests for the bug status dashboard."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_summary_matches_teams():
    """Test that global summary matches sum of team summaries."""
    summary_response = client.get("/api/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()

    teams_response = client.get("/api/teams")
    assert teams_response.status_code == 200
    teams = teams_response.json()["teams"]

    # Verify that total bugs in global summary equals sum of all team totals
    total_from_teams = sum(t["total"] for t in teams)
    assert summary["total_bugs"] == total_from_teams, (
        f"Global summary total_bugs ({summary['total_bugs']}) "
        f"does not match sum of team totals ({total_from_teams})"
    )

    # Verify that blocking bugs match
    blocking_from_teams = sum(t["blocking"] for t in teams)
    assert summary["blocking_bugs"] == blocking_from_teams, (
        f"Global summary blocking_bugs ({summary['blocking_bugs']}) "
        f"does not match sum of team blocking bugs ({blocking_from_teams})"
    )

    # Verify that overdue bugs match
    overdue_from_teams = sum(t["overdue"] for t in teams)
    assert summary["overdue_bugs"] == overdue_from_teams, (
        f"Global summary overdue_bugs ({summary['overdue_bugs']}) "
        f"does not match sum of team overdue bugs ({overdue_from_teams})"
    )


def test_team_detail_page_loads():
    """Test that team detail page loads successfully."""
    response = client.get("/team.html")
    assert response.status_code == 200, (
        f"Expected status code 200 for team.html, got {response.status_code}"
    )
    assert "text/html" in response.headers["content-type"], (
        f"Expected content-type to contain text/html, "
        f"got {response.headers['content-type']}"
    )


def test_index_page_loads():
    """Test that index page loads successfully."""
    response = client.get("/")
    assert response.status_code == 200, (
        f"Expected status code 200 for index page, got {response.status_code}"
    )
    assert "text/html" in response.headers["content-type"], (
        f"Expected content-type to contain text/html, "
        f"got {response.headers['content-type']}"
    )


def test_api_endpoints_return_correct_structure():
    """Test that all API endpoints return the correct data structure."""

    # Test /api/summary structure
    summary_response = client.get("/api/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()

    required_summary_fields = [
        "total_bugs",
        "blocking_bugs",
        "overdue_bugs",
        "need_triage_bugs",
        "snapshot_date",
    ]
    for field in required_summary_fields:
        assert field in summary, f"Missing field '{field}' in /api/summary response"

    # Test /api/teams structure
    teams_response = client.get("/api/teams")
    assert teams_response.status_code == 200
    teams_data = teams_response.json()

    assert "teams" in teams_data, "Missing 'teams' field in /api/teams response"
    teams = teams_data["teams"]

    if len(teams) > 0:
        # Verify structure of first team
        team = teams[0]
        required_team_fields = [
            "team_name",
            "display_name",
            "total",
            "blocking",
            "p0p1",
            "overdue",
        ]
        for field in required_team_fields:
            assert field in team, (
                f"Missing field '{field}' in team object from /api/teams"
            )

        # Test /api/teams/{team_name}/summary structure
        team_name = team["team_name"]
        team_summary_response = client.get(f"/api/teams/{team_name}/summary")
        assert team_summary_response.status_code == 200
        team_summary = team_summary_response.json()

        required_team_summary_fields = [
            "team_name",
            "total_bugs",
            "sla_pass_rate",
            "overdue",
            "has_deadline",
            "by_type",
            "top_assignees",
            "snapshot_date",
        ]
        for field in required_team_summary_fields:
            assert field in team_summary, (
                f"Missing field '{field}' in /api/teams/{team_name}/summary response"
            )

        # Test /api/teams/{team_name}/bugs structure
        team_bugs_response = client.get(f"/api/teams/{team_name}/bugs")
        assert team_bugs_response.status_code == 200
        team_bugs = team_bugs_response.json()

        required_bugs_fields = ["bugs", "total", "snapshot_date"]
        for field in required_bugs_fields:
            assert field in team_bugs, (
                f"Missing field '{field}' in /api/teams/{team_name}/bugs response"
            )

        # If there are bugs, verify bug structure
        if len(team_bugs["bugs"]) > 0:
            bug = team_bugs["bugs"][0]
            required_bug_fields = [
                "bug_id",
                "title",
                "bug_type",
                "state",
                "priority",
                "severity",
                "assigned_to",
                "due_date",
                "created_date",
                "area_path",
                "ado_url",
            ]
            for field in required_bug_fields:
                assert field in bug, (
                    f"Missing field '{field}' in bug object from "
                    f"/api/teams/{team_name}/bugs"
                )

        # Test /api/teams/{team_name}/trend structure
        team_trend_response = client.get(f"/api/teams/{team_name}/trend")
        assert team_trend_response.status_code == 200
        team_trend = team_trend_response.json()

        required_trend_fields = ["dates", "total", "blocking", "p0p1"]
        for field in required_trend_fields:
            assert field in team_trend, (
                f"Missing field '{field}' in /api/teams/{team_name}/trend response"
            )

        # Verify that all trend arrays have the same length
        dates_len = len(team_trend["dates"])
        assert len(team_trend["total"]) == dates_len, (
            "Length of 'total' array does not match 'dates' array in trend data"
        )
        assert len(team_trend["blocking"]) == dates_len, (
            "Length of 'blocking' array does not match 'dates' array in trend data"
        )
        assert len(team_trend["p0p1"]) == dates_len, (
            "Length of 'p0p1' array does not match 'dates' array in trend data"
        )
