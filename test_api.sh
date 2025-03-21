#\!/bin/bash

# Test endpoint for prompt optimization with Claude 3.5 Haiku
curl -X POST http://localhost:8080/api/v1/optimize   -H "Content-Type: application/json"   -d '{
    "user_prompt": "Explain quantum computing to a 10-year-old",
    "target_tasks": ["deduction"],
    "target_behaviors": ["step_by_step", "conciseness"],
    "target_model": "claude-3-5-haiku-latest",
    "domain": "education"
  }' | jq
