#!/bin/bash

# Deploy A1111 WebUI using proven RunPod template
# Single container with web interface - exactly what you want

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

echo -e "${BLUE}🚀 Deploying A1111 WebUI on RunPod${NC}"
echo "=================================="

# Deploy using the proven public template
echo -e "${YELLOW}Creating A1111 WebUI endpoint...${NC}"

# Create the endpoint with A1111 WebUI template
RESPONSE=$(curl -s -X POST "https://api.runpod.ai/v2/endpoints" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "name": "a1111-webui",
  "template": {
    "imageName": "ashleykleynhans/stable-diffusion-webui:latest",
    "containerDiskInGb": 30,
    "volumeInGb": 50,
    "volumeMountPath": "/workspace",
    "ports": "3000/http,8888/http",
    "env": [
      {"key": "JUPYTER_PASSWORD", "value": "RunPod2023!"},
      {"key": "ENABLE_TENSORBOARD", "value": "1"}
    ]
  },
  "workersMin": 0,
  "workersMax": 1,
  "idleTimeout": 5,
  "locations": ["US"],
  "gpuTypes": ["NVIDIA GeForce RTX 4070", "NVIDIA GeForce RTX 4080", "NVIDIA RTX A4000"]
}')

echo "Response: $RESPONSE"

# Try alternative approach with GraphQL
echo -e "${YELLOW}Trying GraphQL API...${NC}"

GRAPHQL_RESPONSE=$(curl -s -X POST "https://api.runpod.ai/graphql" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "query": "mutation { createServerlessEndpoint(input: { name: \"a1111-webui\", templateId: \"runpod/stable-diffusion-webui\", gpuIds: [\"NVIDIA GeForce RTX 4070\", \"NVIDIA GeForce RTX 4080\"], workersMin: 0, workersMax: 1, idleTimeout: 5 }) { id } }"
}')

echo "GraphQL Response: $GRAPHQL_RESPONSE"

# Extract endpoint ID from either response
ENDPOINT_ID=""
if echo "$RESPONSE" | grep -q '"id"'; then
    ENDPOINT_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
elif echo "$GRAPHQL_RESPONSE" | grep -q '"id"'; then
    ENDPOINT_ID=$(echo "$GRAPHQL_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
fi

if [ -n "$ENDPOINT_ID" ]; then
    echo -e "${GREEN}✅ A1111 WebUI endpoint created!${NC}"
    echo "Endpoint ID: $ENDPOINT_ID"
    echo "URL: https://api.runpod.ai/v2/$ENDPOINT_ID"
    
    # Save endpoint info
    cat > a1111_endpoint.txt <<EOF
A1111 WebUI Endpoint
===================
Endpoint ID: $ENDPOINT_ID
API URL: https://api.runpod.ai/v2/$ENDPOINT_ID

To start A1111 WebUI:
1. Send this request to start the container:

curl -X POST "https://api.runpod.ai/v2/$ENDPOINT_ID/run" \\
-H "Authorization: Bearer $RUNPOD_API_KEY" \\
-H "Content-Type: application/json" \\
-d '{
  "input": {
    "cmd": "cd /workspace/stable-diffusion-webui && python webui.py --listen --port 3000 --api --xformers"
  }
}'

2. This will return a job ID
3. The WebUI will be available at the provided URL on port 3000
4. You can also access JupyterLab on port 8888 with password: RunPod2023!
EOF

    echo ""
    echo -e "${GREEN}🎉 Deployment complete!${NC}"
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Check a1111_endpoint.txt for connection details"
    echo "2. Send the API request to start A1111 WebUI"
    echo "3. Access the web interface once it's running"
    
else
    echo -e "${RED}Failed to create endpoint${NC}"
    echo "You may need to use the RunPod web dashboard to create the endpoint manually"
    echo ""
    echo -e "${BLUE}Manual steps:${NC}"
    echo "1. Go to https://runpod.ai/console/serverless"
    echo "2. Click 'New Endpoint'"
    echo "3. Search for 'stable-diffusion-webui' template"
    echo "4. Configure with RTX 4070/4080 GPUs"
    echo "5. Set min workers: 0, max workers: 1"
fi