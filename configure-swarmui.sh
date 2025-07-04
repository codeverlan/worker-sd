#!/bin/bash

# SwarmUI RunPod Backend Configuration Script
# Configures SwarmUI to use all deployed RunPod ComfyUI endpoints

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SWARMUI_CONTAINER="swarmui"
BACKENDS_FILE="/SwarmUI/Data/Backends.fds"

echo -e "${BLUE}🔧 Configuring SwarmUI with RunPod Backends${NC}"
echo "=============================================="

# Check if SwarmUI container is running
if ! docker ps | grep -q "$SWARMUI_CONTAINER"; then
    echo -e "${RED}Error: SwarmUI container '$SWARMUI_CONTAINER' is not running${NC}"
    exit 1
fi

# Check if endpoints.csv exists
if [ ! -f "endpoints.csv" ]; then
    echo -e "${RED}Error: endpoints.csv not found. Run deploy-endpoints.sh first.${NC}"
    exit 1
fi

echo -e "${YELLOW}📝 Backing up current SwarmUI backend configuration...${NC}"

# Backup current configuration
docker exec "$SWARMUI_CONTAINER" cp "$BACKENDS_FILE" "${BACKENDS_FILE}.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true

echo -e "${YELLOW}🔧 Creating new backend configuration...${NC}"

# Start building the new backends configuration
backends_config=""
backend_id=0

# Process each endpoint
while IFS=, read -r model_type endpoint_id url; do
    # Skip header
    if [ "$model_type" = "model_type" ]; then
        continue
    fi
    
    echo -e "${BLUE}  Adding $model_type backend (ID: $backend_id)...${NC}"
    
    # Determine appropriate settings based on model type
    case "$model_type" in
        "SD15")
            title="Stable Diffusion 1.5 (RunPod)"
            ;;
        "SD2")
            title="Stable Diffusion 2.x (RunPod)"
            ;;
        "SDXL")
            title="Stable Diffusion XL (RunPod)"
            ;;
        "SD3")
            title="Stable Diffusion 3 (RunPod)"
            ;;
        "FLUX_SCHNELL")
            title="FLUX.1 Schnell (RunPod)"
            ;;
        "FLUX_DEV")
            title="FLUX.1 Dev (RunPod)"
            ;;
        *)
            title="$model_type (RunPod)"
            ;;
    esac
    
    # Add backend configuration
    backend_config=$(cat <<EOF
$backend_id:
	type: comfyui_api
	title: $title
	enabled: true
	settings:
		#The address of the ComfyUI instance, eg 'http://localhost:8188'.
		Address: $url
		#RunPod API Key for authentication
		APIKey: $RUNPOD_API_KEY
		#Whether the backend is allowed to revert to an 'idle' state if the API address is unresponsive.
		AllowIdle: true
		#How many extra requests may queue up on this backend while one is processing.
		OverQueue: 1
EOF
)
    
    if [ -n "$backends_config" ]; then
        backends_config="$backends_config
$backend_config"
    else
        backends_config="$backend_config"
    fi
    
    backend_id=$((backend_id + 1))
    
done < endpoints.csv

# Write the new configuration to SwarmUI
echo -e "${YELLOW}💾 Writing new configuration to SwarmUI...${NC}"

# Create temporary file with new config
temp_config="/tmp/swarmui_backends.fds"
echo "$backends_config" > "$temp_config"

# Copy to SwarmUI container
docker cp "$temp_config" "$SWARMUI_CONTAINER:$BACKENDS_FILE"

# Clean up
rm "$temp_config"

echo -e "${YELLOW}🔄 Restarting SwarmUI to apply changes...${NC}"

# Restart SwarmUI container to reload configuration
docker restart "$SWARMUI_CONTAINER"

# Wait for SwarmUI to be ready
echo -e "${YELLOW}⏳ Waiting for SwarmUI to restart...${NC}"
sleep 10

max_attempts=30
for attempt in $(seq 1 $max_attempts); do
    if docker logs "$SWARMUI_CONTAINER" --tail 10 2>&1 | grep -q "Server started"; then
        echo -e "${GREEN}✅ SwarmUI restarted successfully!${NC}"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${YELLOW}⚠️  SwarmUI is taking longer than expected to start${NC}"
        echo "Check the container logs: docker logs $SWARMUI_CONTAINER"
    fi
    
    sleep 2
done

echo ""
echo -e "${GREEN}🎉 SwarmUI Configuration Complete!${NC}"
echo "========================================="
echo -e "${BLUE}📊 Configured Backends:${NC}"

# Show configured backends
backend_count=0
while IFS=, read -r model_type endpoint_id url; do
    if [ "$model_type" != "model_type" ]; then
        echo -e "${GREEN}  ✅ $model_type${NC} - $url"
        backend_count=$((backend_count + 1))
    fi
done < endpoints.csv

echo ""
echo -e "${BLUE}📝 Summary:${NC}"
echo "  • Configured $backend_count RunPod backends"
echo "  • SwarmUI is running on: http://localhost:7801"
echo "  • All Stable Diffusion variants are now available"
echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "  1. Open SwarmUI in your browser: http://localhost:7801"
echo "  2. Go to the Server tab to verify backends are loaded"
echo "  3. Test image generation with different models"
echo "  4. Monitor costs in your RunPod dashboard"
echo ""
echo -e "${BLUE}🔍 Troubleshooting:${NC}"
echo "  • Check container logs: docker logs $SWARMUI_CONTAINER"
echo "  • Verify endpoints: ./test-endpoints.sh"
echo "  • Reset config: docker cp \${BACKENDS_FILE}.backup.* $SWARMUI_CONTAINER:$BACKENDS_FILE"