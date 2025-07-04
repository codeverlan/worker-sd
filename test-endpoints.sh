#!/bin/bash

# Test script for all RunPod ComfyUI endpoints

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Auto-load environment  
source "$(dirname "$0")/load-env.sh" || {
    echo -e "${RED}Failed to load environment. Please run: ../setup-runpod-env.sh${NC}"
    exit 1
}

if [ ! -f "endpoints.csv" ]; then
    echo -e "${RED}Error: endpoints.csv not found. Run deploy-endpoints.sh first.${NC}"
    exit 1
fi

echo -e "${BLUE}🧪 Testing All RunPod ComfyUI Endpoints${NC}"
echo "========================================"

# Function to test endpoint
test_endpoint() {
    local model_type=$1
    local endpoint_id=$2
    local url=$3
    
    echo -e "${YELLOW}Testing $model_type endpoint ($endpoint_id)...${NC}"
    
    # Test payload
    test_payload=$(cat <<EOF
{
  "input": {
    "prompt": "a beautiful sunset over mountains, highly detailed, 8k",
    "negative_prompt": "blurry, low quality, text, watermark",
    "model_type": "$model_type",
    "steps": 20,
    "cfg_scale": 7,
    "width": 512,
    "height": 512,
    "sampler_name": "euler"
  }
}
EOF
)
    
    # Submit job (async - correct method)
    response=$(curl -s -m 30 -X POST \
        "$url/run" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$test_payload" 2>&1 || echo '{"error":"request_failed"}')
    
    # Check if job submitted successfully  
    if echo "$response" | grep -q '"id"'; then
        job_id=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        echo -e "${GREEN}✅ $model_type endpoint working (job: $job_id)${NC}"
        
        # Extract and save a sample image if desired
        if command -v jq &> /dev/null; then
            image_data=$(echo "$response" | jq -r '.output.image // empty')
            if [ -n "$image_data" ] && [ "$image_data" != "null" ]; then
                echo "$image_data" | base64 -d > "test_${model_type,,}.png"
                echo "   Sample image saved as test_${model_type,,}.png"
            fi
        fi
    else
        echo -e "${RED}❌ $model_type endpoint failed${NC}"
        echo "Response: $response"
        
        # Check if it's an authentication issue
        if echo "$response" | grep -q "401\|403\|Unauthorized\|Forbidden"; then
            echo -e "${YELLOW}   ⚠️  Authentication issue - check RUNPOD_API_KEY${NC}"
        fi
        
        # Check if endpoint is not found
        if echo "$response" | grep -q "404\|Not Found"; then
            echo -e "${YELLOW}   ⚠️  Endpoint not found - may need to be redeployed${NC}"
        fi
        
        # Check if it's a timeout
        if echo "$response" | grep -q "timeout\|timed out"; then
            echo -e "${YELLOW}   ⚠️  Request timed out - endpoint may be cold starting${NC}"
        fi
    fi
    
    echo ""
}

# Test all endpoints
echo -e "${BLUE}Starting endpoint tests...${NC}"
echo ""

# Skip header line and test each endpoint
tail -n +2 endpoints.csv | while IFS=, read -r model_type endpoint_id url; do
    test_endpoint "$model_type" "$endpoint_id" "$url"
done

echo -e "${GREEN}🎉 Testing complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Check any failed endpoints and redeploy if needed"
echo "2. Use working endpoint URLs in SwarmUI configuration"
echo "3. Run './configure-swarmui.sh' to automatically configure SwarmUI"