#!/bin/bash

# InferPrompt API Demo Script
# This script demonstrates the complete workflow of the InferPrompt API

# Color formatting
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
HR="${YELLOW}--------------------------------------------------------------${NC}"

echo -e "${BLUE}InferPrompt API Demo${NC}"
echo -e "${CYAN}A novel ASP Framework for LLM Prompt Optimization${NC}"
echo -e "${HR}\n"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq is not installed. Output will not be formatted.${NC}"
    JQ_CMD="cat"
else
    JQ_CMD="jq"
fi

# Step 1: Analyze a prompt
echo -e "${GREEN}Step 1: Analyzing a prompt...${NC}"
PROMPT="Explain how black holes work to a high school student"
echo -e "Prompt: ${CYAN}$PROMPT${NC}\n"

ANALYSIS=$(curl -s -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$PROMPT\"}")

echo -e "Analysis Result:"
echo "$ANALYSIS" | $JQ_CMD
echo -e "${HR}\n"

# Step 2: Optimize the prompt
echo -e "${GREEN}Step 2: Optimizing the prompt for Claude...${NC}"

OPTIMIZED=$(curl -s -X POST http://localhost:8080/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d "{
    \"user_prompt\": \"$PROMPT\",
    \"target_tasks\": [\"deduction\"],
    \"target_behaviors\": [\"step_by_step\", \"precision\"],
    \"target_model\": \"claude-3-5-haiku-latest\",
    \"domain\": \"education\"
  }")

echo -e "Optimization Result:"
echo "$OPTIMIZED" | $JQ_CMD
echo -e "${HR}\n"

# Extract the optimized prompt (with or without jq)
if command -v jq &> /dev/null; then
    FULL_PROMPT=$(echo "$OPTIMIZED" | jq -r '.full_prompt')
else
    # This is a simple extraction fallback if jq isn't available
    # It's not robust but should work for demo purposes
    FULL_PROMPT=$(echo "$OPTIMIZED" | grep -o '"full_prompt":"[^"]*"' | sed 's/"full_prompt":"//;s/"//')
fi

# Step 3: Provide feedback
echo -e "${GREEN}Step 3: Providing feedback...${NC}"

FEEDBACK=$(curl -s -X POST http://localhost:8080/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "component_type": "instruction",
    "behavior_type": "precision",
    "effectiveness": 0.95
  }')

echo -e "Feedback Result:"
echo "$FEEDBACK" | $JQ_CMD
echo -e "${HR}\n"

# Step 4: Check prompt history
echo -e "${GREEN}Step 4: Checking prompt history...${NC}"

HISTORY=$(curl -s -X GET "http://localhost:8080/api/v1/history?limit=5&offset=0")

echo -e "History Result:"
echo "$HISTORY" | $JQ_CMD
echo -e "${HR}\n"

echo -e "${BLUE}Demo complete!${NC}"
echo -e "Try running this optimized prompt with the Claude model:"
echo -e "${CYAN}$FULL_PROMPT${NC}\n"