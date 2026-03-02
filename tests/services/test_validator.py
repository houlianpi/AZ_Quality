# tests/services/test_validator.py
from datetime import date, datetime

import pytest

from app.core.team_config import FieldMapping, RequiredFields
from app.services.validator import (
    ValidationError,
    parse_ado_date,
    validate_bug_record,
)


def test_validate_bug_record_valid():
    """Test validation passes for valid bug data."""
    raw_data = {
        "id": 12345,
        "fields": {
            "System.Title": "Test bug",
            "System.State": "Active",
            "System.AssignedTo": {"displayName": "John Doe"},
            "Microsoft.VSTS.Common.Priority": 1,
            "Microsoft.VSTS.Common.Severity": "2 - High",
            "System.AreaPath": "Edge\\Mobile",
            "System.CreatedDate": "2026-02-20T10:30:00Z",
        },
    }

    result, warnings = validate_bug_record(
        raw_data, bug_type="Blocking", snapshot_date=date(2026, 2, 23)
    )

    assert result["bug_id"] == 12345
    assert result["title"] == "Test bug"
    assert result["state"] == "Active"
    assert result["bug_type"] == "Blocking"
    assert result["snapshot_date"] == date(2026, 2, 23)


def test_validate_bug_record_missing_required_field():
    """Test validation fails when required field is missing."""
    raw_data = {
        "id": 12345,
        "fields": {
            # Missing System.Title
            "System.State": "Active",
            "System.CreatedDate": "2026-02-20T10:30:00Z",
        },
    }

    with pytest.raises(ValidationError) as exc_info:
        validate_bug_record(raw_data, bug_type="Blocking", snapshot_date=date(2026, 2, 23))

    assert "title" in str(exc_info.value).lower()


def test_validate_bug_record_truncates_long_assigned_to():
    """Test that assigned_to is truncated to 200 characters."""
    long_name = "A" * 300
    raw_data = {
        "id": 12345,
        "fields": {
            "System.Title": "Test bug",
            "System.State": "Active",
            "System.AssignedTo": {"displayName": long_name},
            "System.CreatedDate": "2026-02-20T10:30:00Z",
        },
    }

    result, warnings = validate_bug_record(
        raw_data, bug_type="Blocking", snapshot_date=date(2026, 2, 23)
    )

    assert len(result["assigned_to"]) == 200


def test_parse_ado_date_iso_format():
    """Test parsing ADO date in ISO format."""
    result = parse_ado_date("2026-02-20T10:30:00Z")
    assert result == datetime(2026, 2, 20, 10, 30, 0)


def test_parse_ado_date_none():
    """Test parsing None returns None."""
    result = parse_ado_date(None)
    assert result is None


def test_validate_bug_record_with_custom_field_mapping():
    """Test validation with custom field mapping."""
    raw_data = {
        "id": 99999,
        "fields": {
            "System.Title": "Custom mapped bug",
            "System.State": "Resolved",
            "Custom.MySLAField": "2026-03-01T00:00:00Z",
        },
    }

    field_mapping = FieldMapping(sla_deadline="Custom.MySLAField")

    result, warnings = validate_bug_record(
        raw_data,
        bug_type="Security",
        snapshot_date=date(2026, 2, 23),
        field_mapping=field_mapping,
    )

    assert result["bug_id"] == 99999
    assert result["sla_deadline"] == date(2026, 3, 1)


def test_validate_bug_record_with_custom_required_fields():
    """Test validation with custom required fields configuration."""
    raw_data = {
        "id": 12345,
        "fields": {
            "System.Title": "Test bug",
            "System.State": "Active",
            # Missing priority - should warn, not fail
        },
    }

    required_fields = RequiredFields(
        required=["bug_id", "title", "state"],
        warn_if_missing=["priority", "assigned_to"],
    )

    result, warnings = validate_bug_record(
        raw_data,
        bug_type="Blocking",
        snapshot_date=date(2026, 2, 23),
        required_fields=required_fields,
    )

    assert result["bug_id"] == 12345
    assert "priority" in str(warnings)
    assert "assigned_to" in str(warnings)


def test_validate_bug_record_custom_required_field_fails():
    """Test validation fails when custom required field is missing."""
    raw_data = {
        "id": 12345,
        "fields": {
            "System.Title": "Test bug",
            "System.State": "Active",
            # Missing priority - required by custom config
        },
    }

    required_fields = RequiredFields(
        required=["bug_id", "title", "state", "priority"],  # priority is required
        warn_if_missing=[],
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_bug_record(
            raw_data,
            bug_type="Blocking",
            snapshot_date=date(2026, 2, 23),
            required_fields=required_fields,
        )

    assert "priority" in str(exc_info.value).lower()
