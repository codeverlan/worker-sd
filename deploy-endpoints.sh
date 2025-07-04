#!/bin/bash

# RunPod Multi-Model Deployment Script
# Provides ready-to-use ComfyUI endpoints for all Stable Diffusion variants

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Auto-load environment
source "$(dirname "$0")/load-env.sh" || {
    echo -e "${RED}Failed to load environment. Please run: ./setup-runpod-env.sh${NC}"
    exit 1
}

echo -e "${BLUE}🚀 RunPod ComfyUI Endpoints Setup for All SD Models${NC}"
echo "====================================================="
echo ""
echo -e "${YELLOW}📋 Since RunPod endpoints are created through the web console,${NC}"
echo -e "${YELLOW}this script will guide you through the manual setup process.${NC}"
echo ""

# Function to display endpoint creation instructions
show_endpoint_instructions() {
    local model_type=$1
    local model_name=$2
    local docker_image=$3
    local gpu_types=$4
    local description=$5
    
    echo -e "${BLUE}📦 $model_name Endpoint${NC}"
    echo -e "${YELLOW}Docker Image:${NC} $docker_image"
    echo -e "${YELLOW}Recommended GPUs:${NC} $gpu_types"
    echo -e "${YELLOW}Description:${NC} $description"
    echo ""
    echo -e "${GREEN}Steps to create:${NC}"
    echo "1. Go to https://www.runpod.io/console/serverless"
    echo "2. Click 'New Endpoint'"
    echo "3. Select 'Docker Image' as source"
    echo "4. Enter Docker image: $docker_image"
    echo "5. Set name: swarmui-comfyui-$model_type"
    echo "6. Configure GPU types: $gpu_types"
    echo "7. Set Max Workers: 3, Idle Timeout: 5 minutes"
    echo "8. Click 'Create Endpoint'"
    echo ""
    echo -e "${YELLOW}After creation, enter the endpoint ID:${NC}"
    read -p "Endpoint ID for $model_name: " endpoint_id
    
    if [ -n "$endpoint_id" ]; then
        endpoint_url="https://api.runpod.ai/v2/$endpoint_id"
        echo "$model_type,$endpoint_id,$endpoint_url" >> endpoints.csv
        echo -e "${GREEN}✅ Saved $model_name endpoint: $endpoint_id${NC}"
        echo "   URL: $endpoint_url"
    else
        echo -e "${RED}❌ Skipped $model_name endpoint${NC}"
    fi
    
    echo ""
    echo "Press Enter to continue to next endpoint..."
    read
    echo ""
}

# Initialize endpoints CSV
echo "model_type,endpoint_id,url" > endpoints.csv

echo -e "${BLUE}🔧 Creating endpoints for all SD models...${NC}"
echo ""

# SD 1.5
show_endpoint_instructions "sd15" "Stable Diffusion 1.5" "runpod/worker-comfyui:latest-base" "RTX 3070, RTX 3080, RTX 4060" "Fast and cost-effective SD 1.5 generation"

# SD 2.x  
show_endpoint_instructions "sd2" "Stable Diffusion 2.x" "runpod/worker-comfyui:latest-base" "RTX 3080, RTX 4070, RTX 4060Ti" "Enhanced quality SD 2.0/2.1 models"

# SDXL
show_endpoint_instructions "sdxl" "Stable Diffusion XL" "runpod/worker-comfyui:latest-sdxl" "RTX 4070, RTX 4080, RTX 4090" "High-resolution SDXL generation"

# SD3
show_endpoint_instructions "sd3" "Stable Diffusion 3" "runpod/worker-comfyui:latest-sd3" "RTX 4080, RTX 4090, A5000" "Latest SD3 model with advanced features"

# FLUX Schnell
show_endpoint_instructions "flux-schnell" "FLUX.1 Schnell" "runpod/worker-comfyui:latest-flux1-schnell" "RTX 4080, RTX 4090, A6000" "Fast FLUX.1 generation"

# FLUX Dev
show_endpoint_instructions "flux-dev" "FLUX.1 Dev" "runpod/worker-comfyui:latest-flux1-dev" "RTX 4090, A6000, A100" "High-quality FLUX.1 generation"

echo -e "${GREEN}🎉 Endpoint setup complete!${NC}"
echo "Endpoint details saved to endpoints.csv"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Wait 2-5 minutes for endpoints to be ready"
echo "2. Test endpoints: ./test-endpoints.sh"
echo "3. Configure SwarmUI: ./configure-swarmui.sh"
echo ""
echo -e "${YELLOW}💡 Tip: Keep your endpoint IDs safe - you'll need them for configuration${NC}"