# Worker-SD (Serverless Stable Diffusion Workers)

Deployment scripts and configurations for running Stable Diffusion and AI workloads on RunPod's serverless GPU infrastructure.

## Overview

This repository contains scripts and configurations to deploy various AI models and services to RunPod, enabling serverless GPU compute for:
- Stable Diffusion (A1111, ComfyUI)
- Text generation models
- Custom AI endpoints
- SwarmUI backends

## Features

- **Easy Deployment**: One-command deployment to RunPod
- **Multiple Frameworks**: Support for A1111, ComfyUI, and custom endpoints
- **Cost Effective**: Serverless model - only pay for actual GPU usage
- **Scalable**: Automatically scales based on demand
- **Integration Ready**: Works with SwarmUI and other frontends

## Prerequisites

- RunPod account with API access
- RunPod API key (set via `setup-runpod-env.sh`)
- Basic understanding of Docker and GPU workloads

## Quick Start

### 1. Setup Environment

```bash
# Set your RunPod API key
./setup-runpod-env.sh
# Enter your API key when prompted
```

### 2. Deploy A1111 (Automatic1111)

```bash
./deploy-a1111.sh
```

This deploys a serverless A1111 instance with:
- Latest A1111 WebUI
- Stable Diffusion models
- API endpoint for generation

### 3. Deploy Custom Endpoints

```bash
./deploy-endpoints.sh
```

Deploys custom GPU endpoints defined in `endpoints.csv`.

## Repository Structure

```
worker-sd/
├── deploy-a1111.sh              # Deploy Automatic1111
├── deploy-endpoints.sh          # Deploy custom endpoints
├── setup-runpod-env.sh         # Configure RunPod API
├── test-endpoint.sh            # Test deployed endpoints
├── runpod-proxy.py            # Proxy for local testing
├── endpoints.csv              # Endpoint configurations
├── swarmui-backends.json      # SwarmUI backend config
├── docs/                      # Documentation
│   ├── A1111_SETUP_GUIDE.md
│   └── ENDPOINT_SETUP_GUIDE.md
└── multi-model-comfyui/       # ComfyUI configurations
    ├── Dockerfile
    └── handler.py
```

## Configuration Files

### endpoints.csv
Defines custom endpoints with their configurations:
```csv
name,gpu_type,container_image,min_workers,max_workers
sd-xl-turbo,RTX_4090,runpod/stable-diffusion:latest,0,3
llama-7b,A100,runpod/llama:7b,1,5
```

### swarmui-backends.json
Configuration for SwarmUI integration:
```json
{
  "backends": [
    {
      "name": "RunPod A1111",
      "url": "https://your-endpoint.runpod.io",
      "type": "a1111"
    }
  ]
}
```

## Deployment Scripts

### deploy-a1111.sh
Deploys Automatic1111 with:
- Persistent model storage
- API access enabled
- Optimized for RunPod serverless

### deploy-endpoints.sh
Batch deploys multiple endpoints from CSV configuration

### test-endpoint.sh
Tests deployed endpoints with sample requests

## Advanced Usage

### Custom Docker Images

Create custom workers with your own Docker images:

```dockerfile
# multi-model-comfyui/Dockerfile
FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

# Install ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /comfyui
WORKDIR /comfyui
RUN pip install -r requirements.txt

# Add custom handler
COPY handler.py /handler.py
CMD ["python", "/handler.py"]
```

### Monitoring and Logs

View endpoint logs:
```bash
# Check endpoint status
curl -H "Authorization: Bearer $RUNPOD_API_KEY" \
  https://api.runpod.io/v1/endpoints/{endpoint_id}/status

# View recent logs
./view-logs.sh {endpoint_id}
```

### Cost Optimization

1. **Set min_workers=0**: Scales to zero when not in use
2. **Use spot instances**: Enable in RunPod dashboard
3. **Optimize models**: Use quantized models when possible
4. **Set idle timeout**: Configure in endpoint settings

## Integration Examples

### Python Client
```python
import requests

endpoint_url = "https://your-endpoint.runpod.io/generate"
headers = {"Authorization": f"Bearer {api_key}"}

response = requests.post(
    endpoint_url,
    headers=headers,
    json={
        "prompt": "a beautiful sunset",
        "steps": 30,
        "width": 512,
        "height": 512
    }
)
```

### SwarmUI Integration
1. Deploy endpoint using scripts
2. Add to `swarmui-backends.json`
3. Import in SwarmUI settings

## Troubleshooting

### Common Issues

1. **Authentication Error**
   - Verify API key is set correctly
   - Check RunPod account has sufficient credits

2. **Deployment Fails**
   - Check GPU availability in your region
   - Verify Docker image exists and is accessible

3. **Endpoint Not Responding**
   - Check logs for startup errors
   - Ensure security groups allow traffic
   - Verify endpoint is in "ready" state

### Debug Mode

Enable verbose logging:
```bash
export RUNPOD_DEBUG=true
./deploy-a1111.sh
```

## Best Practices

1. **Version Control**: Tag deployments for rollback capability
2. **Monitoring**: Set up alerts for endpoint health
3. **Security**: Use environment variables for sensitive data
4. **Testing**: Always test endpoints before production use

## Contributing

1. Fork the repository
2. Create feature branch
3. Test thoroughly with RunPod account
4. Submit pull request with detailed description

## Resources

- [RunPod Documentation](https://docs.runpod.io)
- [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [SwarmUI](https://github.com/mcmonkeyprojects/SwarmUI)

## License

MIT License - see LICENSE file

## Support

- Issues: Create GitHub issue with logs
- RunPod Support: support@runpod.io
- Community: RunPod Discord server