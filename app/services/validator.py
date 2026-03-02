# app/services/validator.py
from datetime import date, datetime
from typing import Any

from app.core.team_config import FieldMapping, RequiredFields


class ValidationError(Exception):
    """Raised when bug data validation fails."""

    pass


class ValidationWarning:
    """Collects warnings during validation."""

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def add(self, message: str) -> None:
        self.warnings.append(message)


def parse_ado_date(value: str | None) -> datetime | None:
    """
    Parse an ADO date string to datetime.

    Args:
        value: Date string in ISO format (e.g., "2026-02-20T10:30:00Z")

    Returns:
        datetime object or None if value is None/empty
    """
    if not value:
        return None

    # Handle ISO format with Z suffix
    if value.endswith("Z"):
        value = value[:-1]

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_blocking(value: Any) -> bool | None:
    """Parse blocking field to boolean."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("yes", "true", "1", "y")
    return bool(value)


def get_field_value(
    raw_data: dict[str, Any],
    field_path: str,
) -> Any:
    """
    Get a field value from raw ADO data.

    Args:
        raw_data: Raw JSON from az boards query
        field_path: ADO field path (e.g., "System.Title")

    Returns:
        Field value or None if not found
    """
    # Special case: ID is at top level
    if field_path == "System.Id":
        return raw_data.get("id")

    fields = raw_data.get("fields", {})
    return fields.get(field_path)


def validate_bug_record(
    raw_data: dict[str, Any],
    bug_type: str,
    snapshot_date: date,
    field_mapping: FieldMapping | None = None,
    required_fields: RequiredFields | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """
    Validate and transform raw ADO bug data into database record format.

    Args:
        raw_data: Raw JSON from az boards query
        bug_type: The bug classification type
        snapshot_date: The snapshot date for this sync
        field_mapping: Custom field mapping (uses defaults if None)
        required_fields: Required field configuration (uses defaults if None)

    Returns:
        Tuple of (dict ready for database insertion, list of warnings)

    Raises:
        ValidationError: If required fields are missing or invalid
    """
    if field_mapping is None:
        field_mapping = FieldMapping()
    if required_fields is None:
        required_fields = RequiredFields()

    warnings: list[str] = []

    # Extract values using field mapping
    bug_id = get_field_value(raw_data, field_mapping.bug_id)
    title = get_field_value(raw_data, field_mapping.title)
    state = get_field_value(raw_data, field_mapping.state)
    assigned_to_data = get_field_value(raw_data, field_mapping.assigned_to)
    priority = get_field_value(raw_data, field_mapping.priority)
    severity = get_field_value(raw_data, field_mapping.severity)
    area_path = get_field_value(raw_data, field_mapping.area_path)
    created_date_str = get_field_value(raw_data, field_mapping.created_date)
    resolved_date_str = get_field_value(raw_data, field_mapping.resolved_date)
    closed_date_str = get_field_value(raw_data, field_mapping.closed_date)

    # New fields
    tags = get_field_value(raw_data, field_mapping.tags)
    due_date_str = get_field_value(raw_data, field_mapping.due_date)
    blocking_raw = get_field_value(raw_data, field_mapping.blocking)
    release = get_field_value(raw_data, field_mapping.release)
    sdl_severity = (
        get_field_value(raw_data, field_mapping.sdl_severity)
        if field_mapping.sdl_severity
        else None
    )

    # Build field values dict for validation
    field_values: dict[str, Any] = {
        "bug_id": bug_id,
        "title": title,
        "state": state,
        "assigned_to": assigned_to_data,
        "priority": priority,
        "severity": severity,
        "area_path": area_path,
        "created_date": created_date_str,
        "resolved_date": resolved_date_str,
        "closed_date": closed_date_str,
        "tags": tags,
        "due_date": due_date_str,
        "blocking": blocking_raw,
        "release": release,
        "sdl_severity": sdl_severity,
    }

    # Validate required fields (using normalized names)
    normalized_required = required_fields.get_normalized_required()
    for field_name in normalized_required:
        value = field_values.get(field_name)
        if value is None or value == "":
            raise ValidationError(f"Missing required field: {field_name}")

    # Check warn_if_missing fields
    normalized_warn = required_fields.get_normalized_warn_if_missing()
    for field_name in normalized_warn:
        value = field_values.get(field_name)
        if value is None or value == "":
            warnings.append(f"Missing field: {field_name}")

    # Build result dict
    result: dict[str, Any] = {
        "snapshot_date": snapshot_date,
        "bug_type": bug_type,
    }

    # Process bug_id
    result["bug_id"] = bug_id

    # Process title
    result["title"] = str(title)[:500] if title else None

    # Process state
    result["state"] = str(state)[:50] if state else None

    # Process assigned_to
    assigned_to = None
    if assigned_to_data:
        if isinstance(assigned_to_data, dict):
            assigned_to = assigned_to_data.get("displayName", "")
        else:
            assigned_to = str(assigned_to_data)
        if len(assigned_to) > 200:
            assigned_to = assigned_to[:200]
    result["assigned_to"] = assigned_to

    # Process priority
    if priority is not None:
        try:
            priority = int(priority)
            if priority < 0 or priority > 4:
                priority = None
        except (ValueError, TypeError):
            priority = None
    result["priority"] = priority

    # Process severity
    result["severity"] = str(severity)[:50] if severity else None

    # Process area_path
    result["area_path"] = str(area_path)[:500] if area_path else None

    # Process tags
    result["tags"] = str(tags)[:500] if tags else None

    # Process blocking
    result["blocking"] = parse_blocking(blocking_raw)

    # Process release
    result["release"] = str(release)[:100] if release else None

    # Process sdl_severity
    result["sdl_severity"] = str(sdl_severity)[:50] if sdl_severity else None

    # Process dates
    result["created_date"] = parse_ado_date(created_date_str)
    result["resolved_date"] = parse_ado_date(resolved_date_str)
    result["closed_date"] = parse_ado_date(closed_date_str)

    # Process due_date
    due_date = None
    if due_date_str:
        parsed = parse_ado_date(due_date_str)
        if parsed:
            due_date = parsed.date()
    result["due_date"] = due_date

    return result, warnings
