#!/bin/bash

# Quick Setup using Public RunPod ComfyUI Endpoints
# Uses existing public endpoints for immediate setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}⚡ Quick Setup: Public RunPod ComfyUI Endpoints${NC}"
echo "==============================================="
echo ""
echo -e "${YELLOW}Using publicly available RunPod ComfyUI endpoints for immediate setup.${NC}"
echo ""

# Initialize endpoints CSV
echo "model_type,endpoint_id,url" > endpoints.csv

# Popular public endpoints (these are examples - you'd use actual public endpoints)
echo -e "${BLUE}📝 Setting up with known public ComfyUI endpoints...${NC}"

# Note: These are template URLs - in practice you'd either:
# 1. Use your own created endpoints
# 2. Use shared/community endpoints if available
# 3. Follow the manual creation process

# Template endpoints for different model types
cat << EOF >> endpoints.csv
sd15,YOUR_SD15_ENDPOINT_ID,https://api.runpod.ai/v2/YOUR_SD15_ENDPOINT_ID
sdxl,YOUR_SDXL_ENDPOINT_ID,https://api.runpod.ai/v2/YOUR_SDXL_ENDPOINT_ID
sd3,YOUR_SD3_ENDPOINT_ID,https://api.runpod.ai/v2/YOUR_SD3_ENDPOINT_ID
flux-schnell,YOUR_FLUX_SCHNELL_ENDPOINT_ID,https://api.runpod.ai/v2/YOUR_FLUX_SCHNELL_ENDPOINT_ID
EOF

echo -e "${YELLOW}📋 To use this quick setup:${NC}"
echo ""
echo "1. Create your own endpoints using the main script:"
echo "   ./deploy-endpoints.sh"
echo ""
echo "2. Or manually edit endpoints.csv with your endpoint IDs:"
echo "   nano endpoints.csv"
echo ""
echo "3. Replace YOUR_*_ENDPOINT_ID with actual endpoint IDs"
echo ""
echo -e "${BLUE}🔗 Popular Community Resources:${NC}"
echo ""
echo "• RunPod Community Discord: https://discord.gg/runpod"
echo "• ComfyUI Templates: https://github.com/runpod-workers"
echo "• Public Endpoints: Check RunPod marketplace"
echo ""

echo -e "${GREEN}Example endpoints.csv format:${NC}"
echo "─────────────────────────────"
cat << EOF
model_type,endpoint_id,url
sd15,abcd1234,https://api.runpod.ai/v2/abcd1234
sdxl,efgh5678,https://api.runpod.ai/v2/efgh5678
sd3,ijkl9012,https://api.runpod.ai/v2/ijkl9012
flux-schnell,mnop3456,https://api.runpod.ai/v2/mnop3456
EOF
echo "─────────────────────────────"
echo ""

echo -e "${YELLOW}⏭️  After updating endpoints.csv:${NC}"
echo "1. Test: ./test-endpoints.sh"
echo "2. Configure SwarmUI: ./configure-swarmui.sh"
echo ""
echo -e "${BLUE}💡 For production use, create your own dedicated endpoints${NC}"
echo -e "${BLUE}   using the full deployment script: ./deploy-endpoints.sh${NC}"