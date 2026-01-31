#!/bin/bash
# Integration test for Worker API
# Tests: create worker -> list workers -> get worker -> delete worker

set -e

# Configuration
TEST_PORT=17788
TEST_DB_DIR="./data/test"
TEST_DB_PATH="${TEST_DB_DIR}/test_worker.db"
BASE_URL="http://127.0.0.1:${TEST_PORT}"
PID_FILE="/tmp/test_worker_api.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"

    # Kill server if running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
            sleep 1
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi

    # Remove test database
    rm -rf "$TEST_DB_DIR"

    echo -e "${GREEN}Cleanup complete${NC}"
}

# Set trap for cleanup
trap cleanup EXIT

# Test result tracking
TESTS_PASSED=0
TESTS_FAILED=0

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

# Wait for server to be ready
wait_for_server() {
    echo "Waiting for server to start..."
    for i in {1..30}; do
        if curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
            echo "Server is ready"
            return 0
        fi
        sleep 0.5
    done
    echo "Server failed to start"
    return 1
}

echo "=================================="
echo "Worker API Integration Test"
echo "=================================="
echo ""

# Prepare test environment
echo -e "${YELLOW}Preparing test environment...${NC}"
mkdir -p "$TEST_DB_DIR"
rm -f "$TEST_DB_PATH"

# Start the server with test configuration
echo -e "${YELLOW}Starting server on port ${TEST_PORT}...${NC}"
DATABASE_PATH="$TEST_DB_PATH" \
PORT="$TEST_PORT" \
LOG_LEVEL="WARNING" \
python3 -m uvicorn app.main:app --host 127.0.0.1 --port "$TEST_PORT" &
echo $! > "$PID_FILE"

# Wait for server
if ! wait_for_server; then
    echo -e "${RED}Failed to start server${NC}"
    exit 1
fi

echo ""
echo "=================================="
echo "Running Tests"
echo "=================================="
echo ""

# Test 1: Health check
echo "Test 1: Health check"
RESPONSE=$(curl -s "${BASE_URL}/api/v1/health")
if echo "$RESPONSE" | grep -q '"status":"healthy"'; then
    pass "Health check returns healthy status"
else
    fail "Health check failed: $RESPONSE"
fi

# Test 2: List workers (should be empty)
echo ""
echo "Test 2: List workers (should be empty)"
RESPONSE=$(curl -s "${BASE_URL}/api/v1/workers")
if echo "$RESPONSE" | grep -q '"workers":\[\]'; then
    pass "Workers list is empty initially"
else
    fail "Workers list should be empty: $RESPONSE"
fi

# Test 3: Create a worker
echo ""
echo "Test 3: Create a worker"
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/workers" \
    -H "Content-Type: application/json" \
    -d '{"type": "claudecode", "env_vars": {"TEST_VAR": "test_value"}, "command_params": ["--verbose"]}')

if echo "$RESPONSE" | grep -q '"type":"claudecode"'; then
    WORKER_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
    pass "Worker created with ID: $WORKER_ID"
else
    fail "Failed to create worker: $RESPONSE"
    WORKER_ID=""
fi

# Test 4: List workers (should have 1 worker)
echo ""
echo "Test 4: List workers (should have 1 worker)"
RESPONSE=$(curl -s "${BASE_URL}/api/v1/workers")
WORKER_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['workers']))" 2>/dev/null || echo "0")
if [ "$WORKER_COUNT" = "1" ]; then
    pass "Workers list has 1 worker"
else
    fail "Workers list should have 1 worker, got: $WORKER_COUNT"
fi

# Test 5: Get worker by ID
echo ""
echo "Test 5: Get worker by ID"
if [ -n "$WORKER_ID" ]; then
    RESPONSE=$(curl -s "${BASE_URL}/api/v1/workers/${WORKER_ID}")
    if echo "$RESPONSE" | grep -q "\"id\":\"${WORKER_ID}\""; then
        pass "Worker retrieved successfully"

        # Verify env_vars
        if echo "$RESPONSE" | grep -q '"TEST_VAR":"test_value"'; then
            pass "Worker env_vars are correct"
        else
            fail "Worker env_vars mismatch"
        fi

        # Verify command_params
        if echo "$RESPONSE" | grep -q '"--verbose"'; then
            pass "Worker command_params are correct"
        else
            fail "Worker command_params mismatch"
        fi
    else
        fail "Failed to get worker: $RESPONSE"
    fi
else
    fail "Cannot test get worker - no worker ID"
fi

# Test 6: Get worker types
echo ""
echo "Test 6: Get worker types"
RESPONSE=$(curl -s "${BASE_URL}/api/v1/workers/types")
if echo "$RESPONSE" | grep -q '"claudecode"'; then
    pass "Worker types include claudecode"
else
    fail "Worker types missing claudecode: $RESPONSE"
fi

# Test 7: Create worker with invalid type
echo ""
echo "Test 7: Create worker with invalid type (should fail)"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/workers" \
    -H "Content-Type: application/json" \
    -d '{"type": "invalid_type"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "400" ]; then
    pass "Invalid worker type rejected with status $HTTP_CODE"
else
    fail "Invalid worker type should be rejected, got status: $HTTP_CODE"
fi

# Test 8: Delete worker
echo ""
echo "Test 8: Delete worker"
if [ -n "$WORKER_ID" ]; then
    RESPONSE=$(curl -s -X DELETE "${BASE_URL}/api/v1/workers/${WORKER_ID}")
    if echo "$RESPONSE" | grep -q '"status":"deleted"'; then
        pass "Worker deleted successfully"
    else
        fail "Failed to delete worker: $RESPONSE"
    fi
else
    fail "Cannot test delete worker - no worker ID"
fi

# Test 9: Verify worker is deleted
echo ""
echo "Test 9: Verify worker is deleted"
RESPONSE=$(curl -s "${BASE_URL}/api/v1/workers")
WORKER_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['workers']))" 2>/dev/null || echo "0")
if [ "$WORKER_COUNT" = "0" ]; then
    pass "Workers list is empty after deletion"
else
    fail "Workers list should be empty after deletion, got: $WORKER_COUNT"
fi

# Test 10: Get deleted worker (should 404)
echo ""
echo "Test 10: Get deleted worker (should 404)"
if [ -n "$WORKER_ID" ]; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/v1/workers/${WORKER_ID}")
    if [ "$HTTP_CODE" = "404" ]; then
        pass "Deleted worker returns 404"
    else
        fail "Deleted worker should return 404, got: $HTTP_CODE"
    fi
else
    fail "Cannot test get deleted worker - no worker ID"
fi

echo ""
echo "=================================="
echo "Test Summary"
echo "=================================="
echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ "$TESTS_FAILED" -gt 0 ]; then
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
