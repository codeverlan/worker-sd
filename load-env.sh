#!/bin/bash

# Quick environment loader for RunPod deployment scripts
# Auto-detects and loads RunPod API key from various sources

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

load_runpod_env() {
    # Check if already loaded
    if [ -n "$RUNPOD_API_KEY" ]; then
        echo -e "${GREEN}✅ RunPod API key already loaded${NC}"
        return 0
    fi
    
    # Try different sources in order of preference
    local sources=(
        "/home/own_emr/.env"
        "$HOME/.runpod_env" 
        "$HOME/.env"
        "$(pwd)/.env"
    )
    
    for source_file in "${sources[@]}"; do
        if [ -f "$source_file" ] && grep -q "RUNPOD_API_KEY" "$source_file" 2>/dev/null; then
            source "$source_file"
            if [ -n "$RUNPOD_API_KEY" ]; then
                echo -e "${GREEN}✅ Loaded RunPod API key from: $source_file${NC}"
                echo -e "${BLUE}Key: ${RUNPOD_API_KEY:0:8}...${NC}"
                return 0
            fi
        fi
    done
    
    # If not found, provide helpful instructions
    echo -e "${RED}❌ RunPod API key not found${NC}"
    echo ""
    echo -e "${YELLOW}💡 To set it up permanently:${NC}"
    echo "   ./setup-runpod-env.sh"
    echo ""
    echo -e "${YELLOW}💡 To set it for this session only:${NC}"
    echo "   export RUNPOD_API_KEY='your_api_key_here'"
    echo ""
    return 1
}

# Auto-load if script is sourced
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    load_runpod_env
else
    # If run directly, just show the function
    echo -e "${BLUE}🔧 RunPod Environment Loader${NC}"
    echo "============================="
    echo ""
    echo "Usage:"
    echo "  source ./load-env.sh    # Load in current shell"
    echo "  ./load-env.sh          # Show this help"
    echo ""
    load_runpod_env
fi