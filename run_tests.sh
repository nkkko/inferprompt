#!/bin/bash

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Ensure we're in the project root directory
cd "$(dirname "$0")"

# Activate the virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Parse arguments
coverage=false
verbose=false
specific_test=""

for arg in "$@"; do
    case $arg in
        --coverage|-c)
            coverage=true
            shift
            ;;
        --verbose|-v)
            verbose=true
            shift
            ;;
        *)
            specific_test=$arg
            shift
            ;;
    esac
done

# Install pytest and pytest-cov if not already installed
echo -e "${GREEN}Checking test dependencies...${NC}"
# Try different ways to install packages
if command -v pip &> /dev/null; then
    pip install pytest pytest-cov pytest-mock > /dev/null 2>&1
elif command -v pip3 &> /dev/null; then
    pip3 install pytest pytest-cov pytest-mock > /dev/null 2>&1
elif command -v python -m pip &> /dev/null; then
    python -m pip install pytest pytest-cov pytest-mock > /dev/null 2>&1
elif command -v python3 -m pip &> /dev/null; then
    python3 -m pip install pytest pytest-cov pytest-mock > /dev/null 2>&1
else
    echo -e "${RED}Could not find pip. Please install manually: pip install pytest pytest-cov pytest-mock${NC}"
fi

# Run the tests
if [ "$coverage" = true ]; then
    echo -e "${GREEN}Running tests with coverage report...${NC}"
    
    if [ -n "$specific_test" ]; then
        if [ "$verbose" = true ]; then
            python -m pytest "$specific_test" -v --cov=app
        else
            python -m pytest "$specific_test" --cov=app
        fi
    else
        if [ "$verbose" = true ]; then
            python -m pytest -v --cov=app
        else
            python -m pytest --cov=app
        fi
    fi
else
    echo -e "${GREEN}Running tests...${NC}"
    
    if [ -n "$specific_test" ]; then
        if [ "$verbose" = true ]; then
            python -m pytest "$specific_test" -v
        else
            python -m pytest "$specific_test"
        fi
    else
        if [ "$verbose" = true ]; then
            python -m pytest -v
        else
            python -m pytest
        fi
    fi
fi

# Check exit code
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed.${NC}"
fi

# Add a note about running specific tests
if [ -z "$specific_test" ]; then
    echo -e "${YELLOW}Tip: Run a specific test file with './run_tests.sh tests/unit/app/models/test_prompt.py'${NC}"
    echo -e "${YELLOW}     Add --coverage (-c) for coverage report or --verbose (-v) for detailed output${NC}"
fi

exit $exit_code