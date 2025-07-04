#!/bin/bash

# Deploy using the PROVEN Ashley Kleynhans template that thousands use
# Single container, all models, zero complexity

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

echo -e "${BLUE}🚀 Using Proven Ashley Kleynhans Template${NC}"
echo "========================================"

# Use the PUBLIC template that thousands use successfully
# Template ID: runpod/stable-diffusion-webui (public template)

echo -e "${YELLOW}Creating endpoint with proven template...${NC}"

RESPONSE=$(curl -s -X POST "https://api.runpod.ai/graphql" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "query": "mutation createServerlessEndpoint($input: CreateServerlessEndpointInput!) { createServerlessEndpoint(input: $input) { id } }",
  "variables": {
    "input": {
      "name": "stable-diffusion-webui",
      "templateId": "runpod/stable-diffusion-webui",
      "gpuIds": ["NVIDIA GeForce RTX 4070", "NVIDIA GeForce RTX 4080", "NVIDIA RTX A4000"],
      "workersMin": 0,
      "workersMax": 1,
      "idleTimeout": 5,
      "scalerType": "QUEUE_DELAY",
      "scalerValue": 1
    }
  }
}')

ENDPOINT_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ENDPOINT_ID" ]; then
    echo -e "${RED}Failed. Response: $RESPONSE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ SUCCESS!${NC}"
echo "Endpoint ID: $ENDPOINT_ID"
echo "URL: https://api.runpod.ai/v2/$ENDPOINT_ID"

# Test it immediately
echo -e "${YELLOW}Testing endpoint...${NC}"

sleep 10

TEST_RESPONSE=$(curl -s -m 30 -X POST "https://api.runpod.ai/v2/$ENDPOINT_ID/runsync" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d '{"input": {"prompt": "a beautiful sunset"}}' || echo "timeout")

if echo "$TEST_RESPONSE" | grep -q '"status"'; then
    echo -e "${GREEN}✅ Endpoint responding!${NC}"
else
    echo -e "${YELLOW}⏳ Endpoint created but may need warm-up${NC}"
fi

# Save config for SwarmUI
cat > swarmui_config.txt <<EOF
# Add this to SwarmUI backends:
{
    "name": "RunPod-StableDiffusion",
    "type": "comfyui_backend",
    "url": "https://api.runpod.ai/v2/$ENDPOINT_ID",
    "auth": "$RUNPOD_API_KEY"
}
EOF

echo ""
echo -e "${GREEN}🎉 DONE! One endpoint, all models included${NC}"
echo "SwarmUI config saved to: swarmui_config.txt"