#!/bin/bash

# Test the feedback endpoint
curl -X POST http://localhost:8080/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "component_type": "instruction",
    "behavior_type": "step_by_step",
    "effectiveness": 0.92
  }' | jq