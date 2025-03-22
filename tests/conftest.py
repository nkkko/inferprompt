import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.models.database import Base, get_db
from app.models.prompt import ComponentType, TaskType, BehaviorType
from app.services.meta_llm import MetaLLMAnalyzer
from app.core.asp_engine import ASPEngine
from app.services.prompt_optimizer import PromptOptimizer

# Disable logging during tests
logging.disable(logging.CRITICAL)

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the tables
Base.metadata.create_all(bind=engine)

# Test fixtures
@pytest.fixture
def test_db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after the test is complete
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    """Create a FastAPI test client with a test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {}

@pytest.fixture
def mock_meta_llm():
    """Create a MetaLLMAnalyzer with mock responses."""
    return MetaLLMAnalyzer(api_key=None)  # None ensures it uses mock responses

@pytest.fixture
def asp_engine():
    """Create an ASPEngine instance for testing."""
    return ASPEngine(load_from_db=False)  # Don't load from DB in tests

@pytest.fixture
def optimizer(mock_meta_llm, asp_engine):
    """Create a PromptOptimizer with mock components."""
    optimizer = PromptOptimizer(api_key=None)
    optimizer.meta_llm = mock_meta_llm
    optimizer.asp_engine = asp_engine
    return optimizer

@pytest.fixture
def sample_prompt_data():
    """Return sample prompt data for testing."""
    return {
        "user_prompt": "Explain quantum computing to a 10-year-old",
        "target_tasks": [TaskType.DEDUCTION],
        "target_behaviors": [BehaviorType.STEP_BY_STEP, BehaviorType.CONCISENESS],
        "target_model": "gpt-3.5-turbo",
        "domain": "education"
    }

@pytest.fixture
def component_types():
    """Return all component types for testing."""
    return [
        ComponentType.INSTRUCTION,
        ComponentType.CONTEXT,
        ComponentType.EXAMPLE,
        ComponentType.CONSTRAINT,
        ComponentType.OUTPUT_FORMAT
    ]

@pytest.fixture
def task_types():
    """Return all task types for testing."""
    return [
        TaskType.DEDUCTION,
        TaskType.INDUCTION,
        TaskType.ABDUCTION,
        TaskType.COMPARISON,
        TaskType.COUNTERFACTUAL
    ]

@pytest.fixture
def behavior_types():
    """Return all behavior types for testing."""
    return [
        BehaviorType.PRECISION,
        BehaviorType.CREATIVITY,
        BehaviorType.STEP_BY_STEP,
        BehaviorType.CONCISENESS,
        BehaviorType.ERROR_CHECKING
    ]