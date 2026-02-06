#!/bin/bash
# Test script for AML Services API

BASE_URL="http://localhost:8000"
API_URL="$BASE_URL/api/v1"

echo "=========================================="
echo "  Testing AML Services API"
echo "=========================================="

echo ""
echo "[1] Health Check:"
curl -s "$BASE_URL/health" | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
echo "[2] Dashboard Stats:"
curl -s "$API_URL/dashboard" | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
echo "[3] Queue Stats:"
curl -s "$API_URL/queue" | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
echo "[4] Users List (limit 5):"
curl -s "$API_URL/users?limit=5" | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
echo "[5] Research Jobs:"
curl -s "$API_URL/research/jobs?limit=5" | python3 -m json.tool 2>/dev/null || echo "Failed"

# Get first user ID for further tests
USER_ID=$(curl -s "$API_URL/users?limit=1" | python3 -c "import sys,json; users=json.load(sys.stdin).get('users',[]); print(users[0]['id'] if users else '')" 2>/dev/null)

if [ -n "$USER_ID" ]; then
  echo ""
  echo "[6] User Status (user_id=$USER_ID):"
  curl -s "$API_URL/user/$USER_ID/status" | python3 -m json.tool 2>/dev/null || echo "Failed"

  echo ""
  echo "[7] User Documents (user_id=$USER_ID):"
  curl -s "$API_URL/documents?user_id=$USER_ID" | python3 -m json.tool 2>/dev/null || echo "Failed"

  echo ""
  echo "[8] User Monitoring (user_id=$USER_ID):"
  curl -s "$API_URL/user/$USER_ID/monitoring" | python3 -m json.tool 2>/dev/null || echo "Failed"

  echo ""
  echo "[9] User Actions (user_id=$USER_ID):"
  curl -s "$API_URL/actions/user/$USER_ID" | python3 -m json.tool 2>/dev/null || echo "Failed"
fi

echo ""
echo "[10] Test Chat Endpoint:"
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "hello"}' | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
echo "=========================================="
echo "  Tests Complete"
echo "=========================================="
