# InferPrompt Development Guide

## Testing the API

### Starting the Server

#### Standard Start
```bash
# Start the server on port 8080
bash run.sh
```

#### Background Start (for testing)
```bash
# Start server in background, save logs and PID
cd /Users/nikola/dev/inferprompt && bash run.sh > server.log 2>&1 & echo $! > server.pid && sleep 3 && echo "Server started in background with PID: $(cat server.pid)"

# Check logs in real-time
tail -f server.log

# Stop the background server
kill $(cat server.pid) && rm server.pid

# If the above doesn't work, find and kill the process more aggressively
ps aux | grep "uvicorn app.main:app" | grep -v grep | awk '{print $2}' | xargs kill -9
```

### API Endpoint Tests

#### Complete Demo
Run the full demo that tests all endpoints in sequence:
```bash
# Run the complete demo script
cd /Users/nikola/dev/inferprompt && ./demo.sh
```

#### Individual Endpoint Tests

1. **Test Optimization with Claude**
```bash
# Optimize a prompt for Claude 3.5 Haiku
cd /Users/nikola/dev/inferprompt && ./test_api.sh
```

2. **Test Prompt Analysis**
```bash
# Analyze a prompt to detect tasks and behaviors
cd /Users/nikola/dev/inferprompt && ./test_analyze.sh
```

3. **Test Feedback Mechanism**
```bash
# Submit feedback to improve optimization
cd /Users/nikola/dev/inferprompt && ./test_feedback.sh
```

4. **Test History Retrieval**
```bash
# Get history of optimized prompts
cd /Users/nikola/dev/inferprompt && ./test_history.sh
```

## Unit Tests

The project includes a comprehensive test suite covering all major components.

### Running Tests

```bash
# Run all tests
cd /Users/nikola/dev/inferprompt && ./run_tests.sh

# Run tests with coverage report
cd /Users/nikola/dev/inferprompt && ./run_tests.sh --coverage

# Run tests with verbose output
cd /Users/nikola/dev/inferprompt && ./run_tests.sh --verbose

# Run a specific test file
cd /Users/nikola/dev/inferprompt && ./run_tests.sh tests/unit/app/models/test_prompt.py
```

### Test Structure

- `tests/conftest.py`: Contains pytest fixtures used across all tests
- `tests/unit/`: Contains unit tests organized by module:
  - `app/api/`: Tests for API endpoints
  - `app/core/`: Tests for core functionality (ASP engine)
  - `app/models/`: Tests for data models
  - `app/services/`: Tests for services (MetaLLM, PromptOptimizer)

### Running Tests Without the Script

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app
```

## Troubleshooting

If you encounter ASP syntax errors in the server logs, this may be due to version incompatibilities with Clingo. The current implementation includes a fallback mechanism that will still provide optimization results even when Clingo fails.

Error example:
```
<block>:XX:XX-XX: error: syntax error, unexpected ., expecting ) or ;
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/optimize` | POST | Optimize a prompt |
| `/api/v1/analyze` | POST | Analyze a prompt |
| `/api/v1/feedback` | POST | Provide feedback |
| `/api/v1/history` | GET | Get optimization history |
| `/api/v1/history/{id}` | GET | Get specific optimized prompt |
| `/api/v1/health` | GET | Health check endpoint |

## Database

SQLite database is created at `./inferprompt.db` on first run. For testing, an in-memory SQLite database is used.

## Development Commands

```bash
# Test against a specific endpoint
curl -X POST "http://localhost:8080/api/v1/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "Explain quantum computing to a 10-year-old",
    "target_tasks": ["deduction"],
    "target_behaviors": ["step_by_step", "conciseness"],
    "target_model": "claude-3-5-haiku-latest",
    "domain": "education"
  }' | jq

# Health check
curl -X GET "http://localhost:8080/api/v1/health" | jq

# Manually commit with standard commit message
cd /Users/nikola/dev/inferprompt && git add . && git commit -m "Update InferPrompt implementation" && git push

# Check server logs in real-time
cd /Users/nikola/dev/inferprompt && tail -f server.log

# Get a specific history entry
curl -X GET "http://localhost:8080/api/v1/history/1" | jq

# Fix potential issues with virtual environment
cd /Users/nikola/dev/inferprompt && rm -rf .venv && bash run.sh --force
```