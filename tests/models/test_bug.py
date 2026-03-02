# tests/models/test_bug.py
from datetime import date, datetime

from app.models.bug import BugRecord


def test_bug_record_creation():
    """Test BugRecord model can be instantiated with all fields."""
    bug = BugRecord(
        snapshot_date=date(2026, 2, 23),
        bug_id=12345,
        title="Test bug title",
        state="Active",
        assigned_to="user@example.com",
        priority=1,
        severity="2-High",
        bug_type="Blocking",
        area_path="Edge\\Mobile",
        sla_deadline=date(2026, 3, 1),
        created_date=datetime(2026, 2, 20, 10, 30, 0),
        resolved_date=None,
        closed_date=None,
    )

    assert bug.bug_id == 12345
    assert bug.title == "Test bug title"
    assert bug.state == "Active"
    assert bug.bug_type == "Blocking"


def test_bug_record_table_name_factory():
    """Test that create_bug_table_class creates table with correct name."""
    from app.models.bug import create_bug_table_class

    EdgeMacBug = create_bug_table_class("edge_mac_bugs")
    assert EdgeMacBug.__tablename__ == "edge_mac_bugs"

    EdgeMobileBug = create_bug_table_class("edge_mobile_bugs")
    assert EdgeMobileBug.__tablename__ == "edge_mobile_bugs"
