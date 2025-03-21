#!/bin/bash

# Test the history endpoint
curl -X GET "http://localhost:8080/api/v1/history?limit=5&offset=0" | jq

# Uncomment after you have at least one prompt in your history:
# curl -X GET "http://localhost:8080/api/v1/history/1" | jq