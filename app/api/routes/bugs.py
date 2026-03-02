# app/api/routes/bugs.py
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.services.bug_service import BugService

router = APIRouter()
bug_service = BugService()


@router.get("/summary")
def get_summary(user: dict[str, Any] = Depends(get_current_user)):
    """Get global summary across all teams."""
    return bug_service.get_global_summary()


@router.get("/teams")
def get_teams(user: dict[str, Any] = Depends(get_current_user)):
    """Get list of teams with summary stats."""
    teams = bug_service.get_teams_overview()
    return {"teams": teams}


@router.get("/teams/{team_name}/summary")
def get_team_summary(team_name: str, user: dict[str, Any] = Depends(get_current_user)):
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
    user: dict[str, Any] = Depends(get_current_user),
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
def get_team_trend(team_name: str, days: int = Query(30), user: dict[str, Any] = Depends(get_current_user)):
    """Get trend data for a team."""
    try:
        return bug_service.get_team_trend(team_name, days=days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/teams/{team_name}/query-links")
def get_team_query_links(team_name: str, user: dict[str, Any] = Depends(get_current_user)):
    """Get ADO query links for a team."""
    try:
        return bug_service.get_team_query_links(team_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/me")
def get_current_user_info(user: dict[str, Any] = Depends(get_current_user)):
    """Get current authenticated user info."""
    return user
