#!/bin/bash

# Fixed test script for RunPod ComfyUI endpoints
# Handles both workflow-based and parameter-based endpoints

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

echo -e "${BLUE}🧪 Testing All RunPod ComfyUI Endpoints (Fixed)${NC}"
echo "=============================================="

# Function to create workflow JSON
create_workflow() {
    local model_type=$1
    local prompt=$2
    local negative_prompt=$3
    
    cat <<EOF
{
  "1": {
    "inputs": {
      "ckpt_name": "model.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "2": {
    "inputs": {
      "text": "$prompt",
      "clip": ["1", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "3": {
    "inputs": {
      "text": "$negative_prompt",
      "clip": ["1", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "4": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
  },
  "5": {
    "inputs": {
      "seed": -1,
      "steps": 10,
      "cfg": 7,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0,
      "model": ["1", 0],
      "positive": ["2", 0],
      "negative": ["3", 0],
      "latent_image": ["4", 0]
    },
    "class_type": "KSampler"
  },
  "6": {
    "inputs": {
      "samples": ["5", 0],
      "vae": ["1", 2]
    },
    "class_type": "VAEDecode"
  },
  "7": {
    "inputs": {
      "filename_prefix": "test_",
      "images": ["6", 0]
    },
    "class_type": "SaveImage"
  }
}
EOF
}

# Function to test endpoint with multiple payload types
test_endpoint() {
    local model_type=$1
    local endpoint_id=$2
    local url=$3
    
    echo -e "${YELLOW}Testing $model_type endpoint ($endpoint_id)...${NC}"
    
    local prompt="a simple test image, beautiful sunset"
    local negative_prompt="blurry, low quality"
    
    # Try parameter-based payload first
    echo "   Trying parameter-based payload..."
    param_payload=$(cat <<EOF
{
  "input": {
    "prompt": "$prompt",
    "negative_prompt": "$negative_prompt",
    "model_type": "$model_type",
    "steps": 10,
    "cfg_scale": 7,
    "width": 512,
    "height": 512,
    "sampler_name": "euler"
  }
}
EOF
)
    
    response=$(timeout 30 curl -s -X POST \
        "$url/runsync" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$param_payload" 2>/dev/null || echo '{"error":"timeout_or_connection_failed"}')
    
    # Check if it worked
    if echo "$response" | grep -q '"status":"COMPLETED"' && echo "$response" | grep -q '"output"'; then
        echo -e "${GREEN}✅ $model_type endpoint working (parameter-based)${NC}"
        return 0
    elif echo "$response" | grep -q '"status":"IN_QUEUE"' || echo "$response" | grep -q '"status":"IN_PROGRESS"'; then
        echo "   Job queued, endpoint is responsive"
        echo -e "${GREEN}✅ $model_type endpoint working (queued job)${NC}"
        return 0
    elif echo "$response" | grep -q "Missing 'workflow' parameter"; then
        echo "   Parameter-based failed, trying workflow-based..."
        
        # Try workflow-based payload
        workflow=$(create_workflow "$model_type" "$prompt" "$negative_prompt")
        workflow_payload=$(cat <<EOF
{
  "input": {
    "workflow": $workflow
  }
}
EOF
)
        
        response=$(timeout 30 curl -s -X POST \
            "$url/runsync" \
            -H "Authorization: Bearer $RUNPOD_API_KEY" \
            -H "Content-Type: application/json" \
            -d "$workflow_payload" 2>/dev/null || echo '{"error":"timeout_or_connection_failed"}')
        
        if echo "$response" | grep -q '"status":"COMPLETED"' && echo "$response" | grep -q '"output"'; then
            echo -e "${GREEN}✅ $model_type endpoint working (workflow-based)${NC}"
            return 0
        elif echo "$response" | grep -q '"status":"IN_QUEUE"' || echo "$response" | grep -q '"status":"IN_PROGRESS"'; then
            echo "   Job queued, endpoint is responsive"
            echo -e "${GREEN}✅ $model_type endpoint working (workflow queued)${NC}"
            return 0
        else
            echo -e "${RED}❌ $model_type endpoint failed (workflow-based)${NC}"
            echo "   Response: $(echo "$response" | head -c 200)"
        fi
    else
        echo -e "${RED}❌ $model_type endpoint failed${NC}"
        echo "   Response: $(echo "$response" | head -c 200)"
        
        # Provide diagnostic info
        if echo "$response" | grep -q "timeout_or_connection_failed"; then
            echo -e "${YELLOW}   ⚠️  Connection timeout - endpoint may be cold or unreachable${NC}"
        elif echo "$response" | grep -q "401\|403\|Unauthorized\|Forbidden"; then
            echo -e "${YELLOW}   ⚠️  Authentication issue - check RUNPOD_API_KEY${NC}"
        elif echo "$response" | grep -q "404\|Not Found"; then
            echo -e "${YELLOW}   ⚠️  Endpoint not found - may need to be redeployed${NC}"
        fi
    fi
    
    echo ""
    return 1
}

# Test all endpoints
echo -e "${BLUE}Starting endpoint tests...${NC}"
echo ""

working_count=0
failed_count=0

# Process endpoints.csv
while IFS=, read -r model_type endpoint_id url; do
    # Skip header and empty lines
    [[ "$model_type" == "model_type" ]] && continue
    [ -z "$model_type" ] && continue
    
    if test_endpoint "$model_type" "$endpoint_id" "$url"; then
        ((working_count++))
    else
        ((failed_count++))
    fi
done < endpoints.csv

echo -e "${BLUE}===============================================${NC}"
echo -e "${GREEN}Working endpoints: $working_count${NC}"
echo -e "${RED}Failed endpoints: $failed_count${NC}"
echo ""

if [ $working_count -gt 0 ]; then
    echo -e "${GREEN}🎉 Some endpoints are working!${NC}"
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Use working endpoints in your SwarmUI configuration"
    echo "2. Redeploy failed endpoints if needed"
    echo "3. Run './configure-swarmui.sh' to configure SwarmUI"
else
    echo -e "${RED}❌ No endpoints are working${NC}"
    echo -e "${BLUE}Troubleshooting steps:${NC}"
    echo "1. Check RUNPOD_API_KEY is correct"
    echo "2. Verify endpoints are deployed: './deploy-endpoints.sh'"
    echo "3. Check RunPod dashboard for endpoint status"
fi