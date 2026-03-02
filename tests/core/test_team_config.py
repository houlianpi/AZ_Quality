# tests/core/test_team_config.py
import tempfile
from pathlib import Path

import pytest
import yaml

from app.core.team_config import TeamConfig, load_team_config, load_all_team_configs


def test_team_config_from_yaml():
    """Test TeamConfig can be loaded from YAML dict."""
    data = {
        "team_name": "edge-mac",
        "table_name": "edge_mac_bugs",
        "queries": {
            "blocking": {
                "query_id": "abc-123",
                "bug_type": "Blocking"
            }
        }
    }
    config = TeamConfig.model_validate(data)

    assert config.team_name == "edge-mac"
    assert config.table_name == "edge_mac_bugs"
    assert len(config.queries) == 1
    assert config.queries["blocking"].query_id == "abc-123"
    assert config.queries["blocking"].bug_type == "Blocking"


def test_load_team_config_from_file():
    """Test loading TeamConfig from a YAML file."""
    yaml_content = """
team_name: edge-mobile
table_name: edge_mobile_bugs
queries:
  blocking:
    query_id: "def-456"
    bug_type: "Blocking"
  a11y:
    query_id: "ghi-789"
    bug_type: "A11y"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        config = load_team_config(Path(f.name))

        assert config.team_name == "edge-mobile"
        assert len(config.queries) == 2


def test_load_all_team_configs():
    """Test loading all team configs from a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two config files
        for team in ["edge_mac", "edge_mobile"]:
            yaml_content = f"""
team_name: {team.replace("_", "-")}
table_name: {team}_bugs
queries:
  blocking:
    query_id: "query-{team}"
    bug_type: "Blocking"
"""
            with open(Path(tmpdir) / f"{team}.yaml", "w") as f:
                f.write(yaml_content)

        configs = load_all_team_configs(Path(tmpdir))

        assert len(configs) == 2
        team_names = {c.team_name for c in configs}
        assert team_names == {"edge-mac", "edge-mobile"}
