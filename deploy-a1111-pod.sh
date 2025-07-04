#!/bin/bash

# Deploy A1111 WebUI as RunPod Pod (simpler approach)
# This gives you a persistent instance with web interface

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

echo -e "${BLUE}🚀 Deploying A1111 WebUI Pod on RunPod${NC}"
echo "====================================="

echo -e "${YELLOW}Creating A1111 WebUI pod...${NC}"

# Create pod using GraphQL API
POD_RESPONSE=$(curl -s -X POST "https://api.runpod.ai/graphql" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "query": "mutation { podFindAndDeployOnDemand(input: { cloudType: ALL, gpuCount: 1, volumeInGb: 50, containerDiskInGb: 20, minVcpuCount: 2, minMemoryInGb: 15, gpuTypeId: \"NVIDIA GeForce RTX 4070\", name: \"a1111-webui\", imageName: \"ashleykleynhans/stable-diffusion-webui:latest\", dockerArgs: \"-p 3000:3001 -p 8888:8888 -e JUPYTER_PASSWORD=RunPod2023!\", ports: \"22/tcp,3000/http,8888/http\", volumeMountPath: \"/workspace\" }) { id, imageName, env, machineId, machine { podHostId } } }"
}')

echo "Pod Response: $POD_RESPONSE"

# Try simpler approach
echo -e "${YELLOW}Trying simpler pod creation...${NC}"

SIMPLE_RESPONSE=$(curl -s -X POST "https://api.runpod.ai/graphql" \
-H "Authorization: Bearer $RUNPOD_API_KEY" \
-H "Content-Type: application/json" \
-d '{
  "query": "mutation { podFindAndDeployOnDemand(input: { cloudType: ALL, gpuCount: 1, gpuTypeId: \"NVIDIA RTX A4000\", name: \"a1111-webui\", imageName: \"runpod/stable-diffusion:web-ui\", ports: \"8888/http,3000/http\" }) { id } }"
}')

echo "Simple Response: $SIMPLE_RESPONSE"

# Extract pod ID
POD_ID=""
if echo "$POD_RESPONSE" | grep -q '"id"'; then
    POD_ID=$(echo "$POD_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
elif echo "$SIMPLE_RESPONSE" | grep -q '"id"'; then
    POD_ID=$(echo "$SIMPLE_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
fi

if [ -n "$POD_ID" ]; then
    echo -e "${GREEN}✅ A1111 WebUI pod created!${NC}"
    echo "Pod ID: $POD_ID"
    
    echo -e "${YELLOW}Waiting for pod to start...${NC}"
    sleep 30
    
    # Get pod details
    POD_DETAILS=$(curl -s -X POST "https://api.runpod.ai/graphql" \
    -H "Authorization: Bearer $RUNPOD_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"query { pod(input: {podId: \\\"$POD_ID\\\"}) { id, name, runtime { ports { ip, isIpPublic, privatePort, publicPort, type } } } }\"}")
    
    echo "Pod Details: $POD_DETAILS"
    
    # Save connection info
    cat > a1111_pod_info.txt <<EOF
A1111 WebUI Pod Information
==========================
Pod ID: $POD_ID

Connection Details:
- Check RunPod console for the public IP and ports
- A1111 WebUI should be available on port 3000
- JupyterLab should be available on port 8888

Steps to connect:
1. Go to https://runpod.ai/console/pods
2. Find your pod: a1111-webui
3. Click "Connect" to see the public IP and ports
4. Access A1111 WebUI at: http://PUBLIC_IP:3000
5. Access JupyterLab at: http://PUBLIC_IP:8888 (password: RunPod2023!)

To start A1111 WebUI (if not auto-started):
1. Connect via SSH or JupyterLab terminal
2. Run: cd /workspace/stable-diffusion-webui && python webui.py --listen --port 3000 --api
EOF

    echo ""
    echo -e "${GREEN}🎉 A1111 WebUI pod deployed!${NC}"
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Check a1111_pod_info.txt for connection details"
    echo "2. Go to https://runpod.ai/console/pods to see your pod"
    echo "3. Click 'Connect' to get the public IP address"
    echo "4. Access A1111 WebUI at http://PUBLIC_IP:3000"
    
else
    echo -e "${RED}Failed to create pod${NC}"
    echo ""
    echo -e "${BLUE}Manual deployment steps:${NC}"
    echo "1. Go to https://runpod.ai/console/pods"
    echo "2. Click 'Deploy' → 'GPU Pod'"
    echo "3. Search for 'stable-diffusion-webui' or use 'ashleykleynhans/stable-diffusion-webui:latest'"
    echo "4. Select RTX 4070 or RTX A4000 GPU"
    echo "5. Set ports: 3000, 8888"
    echo "6. Deploy and wait for it to start"
    echo "7. Connect and access the WebUI"
fi