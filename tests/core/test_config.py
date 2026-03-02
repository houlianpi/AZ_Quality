# tests/core/test_config.py
import os
from unittest.mock import patch


def test_settings_loads_from_env():
    """Test that Settings loads database config from environment variables."""
    env_vars = {
        "MYSQL_HOST": "testhost",
        "MYSQL_PORT": "3307",
        "MYSQL_USER": "testuser",
        "MYSQL_PASSWORD": "testpass",
        "MYSQL_DATABASE": "testdb",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        # Import inside to pick up patched env
        from app.core.config import Settings
        settings = Settings()

        assert settings.MYSQL_HOST == "testhost"
        assert settings.MYSQL_PORT == 3307
        assert settings.MYSQL_USER == "testuser"
        assert settings.MYSQL_PASSWORD == "testpass"
        assert settings.MYSQL_DATABASE == "testdb"


def test_settings_database_url():
    """Test that database_url property returns correct MySQL URL."""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "root",
        "MYSQL_PASSWORD": "secret",
        "MYSQL_DATABASE": "quality_platform",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        from app.core.config import Settings
        settings = Settings()

        expected = "mysql+pymysql://root:secret@localhost:3306/quality_platform"
        assert settings.database_url == expected
