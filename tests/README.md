# InferPrompt Test Suite

This directory contains unit tests for the InferPrompt application.

## Test Structure

- `conftest.py`: Contains pytest fixtures used across all tests
- `unit/`: Contains unit tests organized by module
  - `app/`: Tests for app modules
    - `api/`: Tests for API endpoints
    - `core/`: Tests for core functionality
    - `models/`: Tests for data models
    - `services/`: Tests for services

## Running Tests

To run all tests:

```bash
cd /path/to/inferprompt
python -m pytest
```

To run tests with coverage report:

```bash
cd /path/to/inferprompt
python -m pytest --cov=app
```

To run a specific test file:

```bash
cd /path/to/inferprompt
python -m pytest tests/unit/app/models/test_prompt.py
```

## Test Design

- Unit tests use pytest fixtures defined in conftest.py
- Database operations use an in-memory SQLite database
- External services (like OpenAI API) are mocked
- API tests use the FastAPI TestClient

## Adding New Tests

When adding new tests:

1. Identify the module to test
2. Create or update the corresponding test file in the appropriate directory
3. Use existing fixtures where possible
4. Follow the existing naming conventions and patterns

## Testing Approach

- Each module has its own test file
- Tests focus on individual units of functionality
- Mock external dependencies to ensure tests are fast and reliable
- Test both happy paths and error handling