#!/bin/bash
# Test script for Inference Engine API

BASE_URL="http://localhost:8000/api/v1"

echo "=========================================="
echo "  Testing Inference Engine API"
echo "=========================================="

echo ""
echo "[1] Health Check:"
curl -s "$BASE_URL/health" | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
echo "[2] Async System Health:"
curl -s "$BASE_URL/health/async" | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
echo "[3] Queue Stats:"
curl -s "$BASE_URL/async/stats" | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
echo "[4] Submit Test Task:"
RESULT=$(curl -s -X POST "$BASE_URL/async/submit" \
  -H "Content-Type: application/json" \
  -d '{"task_type": "generate", "payload": {"prompt": "Say hello"}}')
echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"

TASK_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null)

if [ -n "$TASK_ID" ]; then
  echo ""
  echo "[5] Check Task Status (waiting 3s):"
  sleep 3
  curl -s "$BASE_URL/async/status/$TASK_ID" | python3 -m json.tool 2>/dev/null || echo "Failed"
fi

echo ""
echo "=========================================="
echo "  Tests Complete"
echo "=========================================="
