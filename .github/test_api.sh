#!/bin/bash
# Test script for Inference Engine API
# Run from the instance after setup

BASE_URL="http://localhost:5000/api/v1"

echo "=== Testing Inference Engine API ==="
echo ""

echo "1. Health Check:"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

echo "2. Async System Health:"
curl -s "$BASE_URL/health/async" | python3 -m json.tool
echo ""

echo "3. Queue Stats:"
curl -s "$BASE_URL/async/stats" | python3 -m json.tool
echo ""

echo "4. Submit Test Task (generate):"
RESULT=$(curl -s -X POST "$BASE_URL/async/submit" \
  -H "Content-Type: application/json" \
  -d '{"task_type": "generate", "payload": {"prompt": "Say hello in one word"}}')
echo "$RESULT" | python3 -m json.tool

TASK_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))")
echo ""

if [ -n "$TASK_ID" ]; then
  echo "5. Check Task Status (task_id: $TASK_ID):"
  sleep 2
  curl -s "$BASE_URL/async/status/$TASK_ID" | python3 -m json.tool
fi

echo ""
echo "=== Tests Complete ==="
