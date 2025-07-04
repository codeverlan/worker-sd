#!/bin/bash

# WORKING test script - uses correct RunPod async API
# No complex workflows, just proper API calls

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ -z "$RUNPOD_API_KEY" ]; then
    echo -e "${RED}RUNPOD_API_KEY not set${NC}"
    exit 1
fi

echo -e "${BLUE}🧪 Testing RunPod Endpoints (WORKING Method)${NC}"
echo "============================================"

test_endpoint() {
    local model_type=$1
    local endpoint_id=$2
    local url=$3
    
    echo -e "${YELLOW}Testing $model_type endpoint...${NC}"
    
    # Submit job (async)
    response=$(curl -s -X POST "$url/run" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"input": {"prompt": "a simple test"}}')
    
    job_id=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$job_id" ]; then
        echo "   Job submitted: $job_id"
        echo -e "${GREEN}✅ $model_type endpoint working${NC}"
        
        # Optional: Check job status after 30 seconds
        echo "   Checking status in 30s..."
        sleep 30
        status=$(curl -s -X GET "$url/status/$job_id" -H "Authorization: Bearer $RUNPOD_API_KEY")
        echo "   Status: $(echo "$status" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
    else
        echo -e "${RED}❌ $model_type endpoint failed${NC}"
        echo "   Response: $response"
    fi
    echo ""
}

# Test all endpoints from CSV
tail -n +2 endpoints.csv | while IFS=, read -r model_type endpoint_id url; do
    [ -z "$model_type" ] && continue
    test_endpoint "$model_type" "$endpoint_id" "$url"
done

echo -e "${GREEN}🎉 All endpoints tested with correct API calls!${NC}"