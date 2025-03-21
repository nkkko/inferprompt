#!/bin/bash

# Test the analyze endpoint
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Explain the process of photosynthesis in simple terms"
  }' | jq