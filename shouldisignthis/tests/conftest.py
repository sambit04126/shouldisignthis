import os
import pytest
import logging

# Set config path BEFORE importing app modules
os.environ["SHOULDISIGNTHIS_CONFIG_PATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "../test_config.yaml"))

from shouldisignthis.config import configure_logging

@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Configures logging to 'tests.log' for all test runs."""
    configure_logging(
        log_file_override="tests.log",
        log_level_override=logging.DEBUG
    )
