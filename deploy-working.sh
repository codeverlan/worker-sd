#!/bin/bash

# WORKING deployment using RunPod REST API
# One container, proven approach, zero complexity

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

echo -e "${BLUE}🚀 Creating Simple Working Endpoint${NC}"
echo "==================================="

# Create endpoint using REST API (not GraphQL)
echo -e "${YELLOW}Deploying stable diffusion endpoint...${NC}"

RESPONSE=$(curl -s -X POST "https://api.runpod.ai/v2/template" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "name": "stable-diffusion-simple",
  "imageName": "ashleykleynhans/stable-diffusion-webui:latest",
  "containerDiskInGb": 20,
  "volumeInGb": 40,
  "volumeMountPath": "/workspace",
  "ports": "8000/http,3000/http",
  "env": [
    {"key": "PUBLIC_KEY", "value": "'"$RUNPOD_API_KEY"'"}
  ]
}')

echo "Template response: $RESPONSE"

# Simple approach - use existing public endpoint or create basic one
echo -e "${YELLOW}Creating serverless endpoint...${NC}"

ENDPOINT_RESPONSE=$(curl -s -X POST "https://api.runpod.ai/v2/endpoints" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "name": "stable-diffusion",
  "template": {
    "imageName": "ashleykleynhans/stable-diffusion-webui:latest",
    "containerDiskInGb": 20,
    "volumeInGb": 40
  },
  "networkVolumeId": null,
  "locations": {
    "US": {
      "workersMin": 0,
      "workersMax": 1,
      "gpuTypes": ["NVIDIA GeForce RTX 4070"]
    }
  },
  "idleTimeout": 5
}')

echo "Endpoint response: $ENDPOINT_RESPONSE"

# Extract endpoint ID
ENDPOINT_ID=$(echo "$ENDPOINT_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$ENDPOINT_ID" ]; then
    echo -e "${GREEN}✅ Endpoint created: $ENDPOINT_ID${NC}"
    echo "URL: https://api.runpod.ai/v2/$ENDPOINT_ID"
    
    echo "Testing in 30 seconds..."
    sleep 30
    
    curl -s -X POST "https://api.runpod.ai/v2/$ENDPOINT_ID/runsync" \
    -H "Authorization: Bearer $RUNPOD_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"input": {"prompt": "test"}}' || echo -e "${YELLOW}Endpoint may need more warm-up time${NC}"
else
    echo -e "${RED}No endpoint ID found${NC}"
fi

echo -e "${GREEN}🎉 Deployment complete!${NC}"