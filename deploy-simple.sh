#!/bin/bash

# Simple RunPod Deployment - ONE container with everything
# Based on proven ashleykleynhans/stable-diffusion-docker template

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ -z "$RUNPOD_API_KEY" ]; then
    echo -e "${RED}Error: RUNPOD_API_KEY not set${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 Deploying Simple RunPod Stable Diffusion Container${NC}"
echo "=================================================="

# Create the unified endpoint
echo -e "${YELLOW}Creating unified stable diffusion endpoint...${NC}"

# Use the proven template approach
curl -s -X POST "https://api.runpod.ai/graphql" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "query": "mutation { saveTemplate(input: { containerDiskInGb: 50, dockerArgs: \"-p 3000:3001 -p 8888:8888 -p 2999:2999 -p 6006:6006 -p 8000:8000\", env: [{ key: \"JUPYTER_PASSWORD\", value: \"Jup1t3R!\" }], imageName: \"ashleykleynhans/stable-diffusion-webui:latest\", isPublic: false, name: \"Stable Diffusion WebUI\", readme: \"# Stable Diffusion WebUI\\n\\nThis template includes:\\n- Automatic1111 WebUI\\n- ComfyUI\\n- All major models\\n- JupyterLab\\n\\nPorts:\\n- 3000: A1111 WebUI\\n- 8888: JupyterLab\\n- 2999: ComfyUI\\n\", volumeInGb: 50, volumeMountPath: \"/workspace\" }) { id } }"
}' | grep -o '"id":"[^"]*"' | cut -d'"' -f4 > /tmp/template_id.txt

TEMPLATE_ID=$(cat /tmp/template_id.txt)

if [ -z "$TEMPLATE_ID" ]; then
    echo -e "${RED}Failed to create template${NC}"
    exit 1
fi

echo "Template ID: $TEMPLATE_ID"

# Create the serverless endpoint
echo -e "${YELLOW}Creating serverless endpoint...${NC}"

ENDPOINT_RESPONSE=$(curl -s -X POST "https://api.runpod.ai/graphql" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d "{
  \"query\": \"mutation { createServerlessEndpoint(input: { gpuIds: [\\\"NVIDIA RTX A4000\\\", \\\"NVIDIA GeForce RTX 4070\\\", \\\"NVIDIA GeForce RTX 4080\\\"], idleTimeout: 5, locations: [\\\"US\\\"], name: \\\"stable-diffusion-unified\\\", networkVolumeId: null, scalerType: \\\"QUEUE_DELAY\\\", scalerValue: 4, templateId: \\\"$TEMPLATE_ID\\\", workersMax: 3, workersMin: 0 }) { id } }\"
}")

ENDPOINT_ID=$(echo "$ENDPOINT_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ENDPOINT_ID" ]; then
    echo -e "${RED}Failed to create endpoint${NC}"
    echo "Response: $ENDPOINT_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Endpoint created successfully!${NC}"
echo "Endpoint ID: $ENDPOINT_ID"
echo "URL: https://api.runpod.ai/v2/$ENDPOINT_ID"

# Save the endpoint info
cat > /tmp/unified_endpoint.txt <<EOF
Unified Stable Diffusion Endpoint
=================================
Endpoint ID: $ENDPOINT_ID
URL: https://api.runpod.ai/v2/$ENDPOINT_ID
Template ID: $TEMPLATE_ID

Services Available:
- A1111 WebUI: Port 3000
- ComfyUI: Port 2999  
- JupyterLab: Port 8888

Test Command:
curl -X POST "https://api.runpod.ai/v2/$ENDPOINT_ID/runsync" \\
-H "Authorization: Bearer \$RUNPOD_API_KEY" \\
-H "Content-Type: application/json" \\
-d '{"input": {"cmd": "python /workspace/stable-diffusion-webui/webui.py --listen --port 3000 --api"}}'
EOF

echo ""
echo -e "${GREEN}🎉 Simple deployment complete!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo "1. Test the endpoint: curl the URL above"
echo "2. Configure SwarmUI to use: https://api.runpod.ai/v2/$ENDPOINT_ID"
echo "3. All models are included in one container"
echo ""
echo "Endpoint details saved to: /tmp/unified_endpoint.txt"