"""Pytest configuration and shared fixtures for AISRE tests."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))

# Set test environment variables
os.environ.setdefault("NVIDIA_API_KEY", "test-key-not-real")
os.environ.setdefault("PLATFORM", "docker")
os.environ.setdefault("VICTIM_CONTAINER", "victim-app")
os.environ.setdefault("VICTIM_HEALTH_URL", "http://localhost:8000/health")
os.environ.setdefault("VICTIM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("ATLAS_URL", "http://localhost:8087")
os.environ.setdefault("ATLAS_PRINCIPAL", "spiffe://test/principal")
os.environ.setdefault("ATLAS_DELEGATE", "spiffe://test/delegate")
os.environ.setdefault("APPROVAL_TOKEN", "test-approval-token")
os.environ.setdefault("ENABLE_DEMO", "true")


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker

    from database import Base
    import models  # Ensure models are registered with Base

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    engine = sqlalchemy.create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield SessionLocal

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def mock_docker():
    """Mock docker subprocess calls."""
    with patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_httpx():
    """Mock httpx calls."""
    with patch("httpx.AsyncClient") as mock_client:
        yield mock_client


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    with patch("openai.OpenAI") as mock_client:
        yield mock_client


@pytest.fixture
def sample_incident():
    """Create a sample incident for testing."""
    from models import Incident
    from datetime import datetime

    incident = Incident(
        id=1,
        status="open",
        service_name="victim-app",
        opened_at=datetime.utcnow(),
    )
    return incident


@pytest.fixture(autouse=True)
def reset_modules():
    """Reset module-level state between tests."""
    # Reset poller's active_incident_id
    import poller
    poller.active_incident_id = None

    # Reset agent's _client
    import agent
    agent._client = None

    # Reset remediation's atlas client
    import remediation
    remediation.atlas = None

    yield


# Test markers
def pytest_configure(config):
    config.addinivalue_line("markers", "xfail_strict: mark test as expected to fail (strict)")


# Helper for strict xfail
def xfail_strict(reason: str):
    """Decorator for tests that should fail (reproducing defects)."""
    return pytest.mark.xfail(strict=True, reason=reason)