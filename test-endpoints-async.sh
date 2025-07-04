#!/bin/bash

# Async test script for RunPod ComfyUI endpoints
# Handles slow-starting endpoints and queued jobs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

RUNPOD_API_KEY="${RUNPOD_API_KEY}"

if [ -z "$RUNPOD_API_KEY" ]; then
    echo -e "${RED}Error: RUNPOD_API_KEY environment variable not set${NC}"
    exit 1
fi

if [ ! -f "endpoints.csv" ]; then
    echo -e "${RED}Error: endpoints.csv not found. Run deploy-endpoints.sh first.${NC}"
    exit 1
fi

echo -e "${BLUE}🧪 Testing All RunPod ComfyUI Endpoints (Async Mode)${NC}"
echo "=================================================="

# Function to submit job
submit_job() {
    local model_type=$1
    local endpoint_id=$2
    local url=$3
    
    # Simple test payload
    test_payload=$(cat <<EOF
{
  "input": {
    "prompt": "a simple test image, red flower",
    "negative_prompt": "blurry",
    "model_type": "$model_type",
    "steps": 10,
    "cfg_scale": 7,
    "width": 512,
    "height": 512
  }
}
EOF
)
    
    # Submit job
    response=$(curl -s -m 30 -X POST \
        "$url/runsync" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$test_payload" 2>&1)
    
    echo "$response"
}

# Function to check job status
check_job_status() {
    local job_id=$1
    local url=$2
    
    response=$(curl -s -m 10 -X GET \
        "$url/status/$job_id" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" 2>&1)
    
    echo "$response"
}

# Function to test endpoint with async handling
test_endpoint_async() {
    local model_type=$1
    local endpoint_id=$2
    local url=$3
    
    echo -e "${YELLOW}Testing $model_type endpoint ($endpoint_id)...${NC}"
    
    # Submit job
    response=$(submit_job "$model_type" "$endpoint_id" "$url")
    
    # Check response
    if echo "$response" | grep -q '"id"'; then
        # Job submitted successfully
        job_id=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        
        echo "   Job submitted: $job_id (status: $status)"
        
        if [ "$status" = "COMPLETED" ]; then
            if echo "$response" | grep -q '"status":"COMPLETED".*"output"'; then
                echo -e "${GREEN}✅ $model_type endpoint working correctly (immediate completion)${NC}"
            else
                echo -e "${RED}❌ $model_type endpoint completed but no output${NC}"
            fi
        elif [ "$status" = "IN_QUEUE" ] || [ "$status" = "IN_PROGRESS" ]; then
            echo "   Job queued/running, checking status..."
            
            # Wait and check status
            for i in {1..12}; do  # 2 minutes max
                sleep 10
                status_response=$(check_job_status "$job_id" "$url")
                
                if echo "$status_response" | grep -q '"status":"COMPLETED"'; then
                    if echo "$status_response" | grep -q '"output"'; then
                        echo -e "${GREEN}✅ $model_type endpoint working correctly (completed after ${i}0s)${NC}"
                        break
                    else
                        echo -e "${RED}❌ $model_type endpoint completed but no output${NC}"
                        break
                    fi
                elif echo "$status_response" | grep -q '"status":"FAILED"'; then
                    echo -e "${RED}❌ $model_type endpoint failed during execution${NC}"
                    echo "   Error: $(echo "$status_response" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)"
                    break
                fi
                
                if [ $i -eq 12 ]; then
                    echo -e "${YELLOW}⏱️ $model_type endpoint timeout (still running after 2 minutes)${NC}"
                fi
            done
        else
            echo -e "${RED}❌ $model_type endpoint failed${NC}"
            echo "   Response: $response"
        fi
    else
        echo -e "${RED}❌ $model_type endpoint failed to submit job${NC}"
        echo "   Response: $response"
        
        # Provide helpful error messages
        if echo "$response" | grep -q "401\|403\|Unauthorized\|Forbidden"; then
            echo -e "${YELLOW}   ⚠️  Authentication issue - check RUNPOD_API_KEY${NC}"
        elif echo "$response" | grep -q "404\|Not Found"; then
            echo -e "${YELLOW}   ⚠️  Endpoint not found - may need to be redeployed${NC}"
        elif echo "$response" | grep -q "timeout\|timed out"; then
            echo -e "${YELLOW}   ⚠️  Request timed out - endpoint may be unavailable${NC}"
        fi
    fi
    
    echo ""
}

# Test all endpoints
echo -e "${BLUE}Starting async endpoint tests...${NC}"
echo ""

# Process endpoints.csv
tail -n +2 endpoints.csv | while IFS=, read -r model_type endpoint_id url; do
    # Skip empty lines
    [ -z "$model_type" ] && continue
    
    test_endpoint_async "$model_type" "$endpoint_id" "$url"
done

echo -e "${GREEN}🎉 Async testing complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Check any failed endpoints and redeploy if needed"
echo "2. Use working endpoint URLs in SwarmUI configuration"
echo "3. Run './configure-swarmui.sh' to automatically configure SwarmUI"