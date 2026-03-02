# app/core/team_config.py
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class QueryConfig(BaseModel):
    """Configuration for a single ADO query."""

    query_id: str
    bug_type: str


class FieldMapping(BaseModel):
    """Mapping from ADO field names to database column names."""

    # Required fields
    bug_id: str = Field(default="System.Id", description="Bug ID field")
    title: str = Field(default="System.Title", description="Title field")
    state: str = Field(default="System.State", description="State field")

    # Optional fields
    assigned_to: str = Field(default="System.AssignedTo", description="Assigned To field")
    priority: str = Field(default="Microsoft.VSTS.Common.Priority", description="Priority field")
    severity: str = Field(default="Microsoft.VSTS.Common.Severity", description="Severity field")
    area_path: str = Field(default="System.AreaPath", description="Area Path field")
    created_date: str = Field(default="System.CreatedDate", description="Created Date field")
    resolved_date: str = Field(
        default="Microsoft.VSTS.Common.ResolvedDate", description="Resolved Date field"
    )
    closed_date: str = Field(
        default="Microsoft.VSTS.Common.ClosedDate", description="Closed Date field"
    )

    # New fields
    tags: str = Field(default="System.Tags", description="Tags field")
    due_date: str = Field(
        default="Microsoft.VSTS.Scheduling.DueDate", description="Due Date field"
    )
    blocking: str = Field(
        default="Microsoft.VSTS.Common.Blocking", description="Blocking field"
    )
    release: str = Field(
        default="Microsoft.VSTS.Common.Release", description="Release field"
    )
    sdl_severity: str | None = Field(
        default=None, description="SDL Severity field (custom, set if available)"
    )


# Mapping from ADO Column display names to internal field names
ADO_COLUMN_TO_FIELD: dict[str, str] = {
    # Standard columns
    "ID": "bug_id",
    "Title": "title",
    "State": "state",
    "Assigned To": "assigned_to",
    "Priority": "priority",
    "Severity": "severity",
    "Area Path": "area_path",
    "Created Date": "created_date",
    "Resolved Date": "resolved_date",
    "Closed Date": "closed_date",
    "Tags": "tags",
    "Due Date": "due_date",
    "Blocking": "blocking",
    "Release": "release",
    "SDL Severity": "sdl_severity",
}


def normalize_field_name(name: str) -> str:
    """
    Convert ADO Column display name to internal field name.

    Args:
        name: ADO Column name (e.g., "Assigned To") or internal name (e.g., "assigned_to")

    Returns:
        Internal field name
    """
    # If it's already an internal name, return as-is
    if name in ADO_COLUMN_TO_FIELD.values():
        return name

    # Try to map from ADO Column name
    return ADO_COLUMN_TO_FIELD.get(name, name.lower().replace(" ", "_"))


class RequiredFields(BaseModel):
    """Configuration for which fields are required vs optional."""

    # Fields that must have values (validation will fail if missing)
    # Can use ADO Column names ("Assigned To") or internal names ("assigned_to")
    required: list[str] = Field(
        default=["bug_id", "title", "state"],
        description="Fields that must have non-null values",
    )

    # Fields to warn about if missing (but still allow)
    warn_if_missing: list[str] = Field(
        default=[],
        description="Fields to warn about if missing",
    )

    def get_normalized_required(self) -> list[str]:
        """Get required fields as internal field names."""
        return [normalize_field_name(f) for f in self.required]

    def get_normalized_warn_if_missing(self) -> list[str]:
        """Get warn_if_missing fields as internal field names."""
        return [normalize_field_name(f) for f in self.warn_if_missing]


class TeamConfig(BaseModel):
    """Configuration for a team's bug sync."""

    team_name: str
    table_name: str
    queries: dict[str, QueryConfig]

    # Field configuration (optional, uses defaults if not specified)
    field_mapping: FieldMapping = Field(default_factory=FieldMapping)
    required_fields: RequiredFields = Field(default_factory=RequiredFields)


def load_team_config(config_path: Path) -> TeamConfig:
    """
    Load a team configuration from a YAML file.

    Args:
        config_path: Path to the YAML config file

    Returns:
        TeamConfig object

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is invalid
        pydantic.ValidationError: If config structure is invalid
    """
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return TeamConfig.model_validate(data)


def load_all_team_configs(config_dir: Path, team_filter: str | None = None) -> list[TeamConfig]:
    """
    Load all team configurations from a directory.

    Args:
        config_dir: Directory containing YAML config files
        team_filter: Optional team name to filter (loads only that team)

    Returns:
        List of TeamConfig objects
    """
    configs = []

    for yaml_file in sorted(config_dir.glob("*.yaml")):
        config = load_team_config(yaml_file)

        if team_filter is None or config.team_name == team_filter:
            configs.append(config)

    return configs
