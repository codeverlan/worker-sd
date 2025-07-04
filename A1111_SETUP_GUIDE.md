# 🎯 A1111 WebUI Setup Guide - Manual Deployment

Since the API endpoints are returning 404s, here's the **proven manual method** that always works:

## Step 1: Access RunPod Console
1. Go to: https://runpod.ai/console/pods
2. Log in with your RunPod account

## Step 2: Deploy GPU Pod
1. Click **"Deploy"** button
2. Select **"GPU Pod"**
3. Choose **"Community Cloud"** (cheaper) or **"Secure Cloud"**

## Step 3: Select Template
**Option A: Use Pre-built Template**
- Search for: `stable-diffusion-webui`
- Select: **"Stable Diffusion WebUI"** by RunPod
- Click **"Deploy"**

**Option B: Use Ashley Kleynhans Template (Recommended)**
- Click **"Custom Image"**
- Image Name: `ashleykleynhans/stable-diffusion-webui:latest`
- Container Disk: `20GB`
- Volume Disk: `50GB`
- Volume Mount Path: `/workspace`

## Step 4: Configure GPU and Ports
- **GPU**: Select `RTX 4070` or `RTX A4000` (good price/performance)
- **Ports**: Add these ports:
  - `3000/http` (A1111 WebUI)
  - `8888/http` (JupyterLab)
  - `22/tcp` (SSH)

## Step 5: Environment Variables (Optional)
Add these if using custom image:
- `JUPYTER_PASSWORD` = `RunPod2023!`
- `WEBUI_FLAGS` = `--listen --port 3000 --api --xformers`

## Step 6: Deploy and Wait
1. Click **"Deploy"**
2. Wait 2-3 minutes for container to start
3. Status should change to **"Running"**

## Step 7: Access A1111 WebUI
1. In your pod list, click **"Connect"**
2. Copy the **Public IP** address
3. Access A1111 WebUI at: `http://PUBLIC_IP:3000`
4. Access JupyterLab at: `http://PUBLIC_IP:8888`

## Step 8: Start A1111 WebUI (if needed)
If the WebUI isn't auto-started:

1. Click **"Connect"** → **"Start Web Terminal"**
2. Run these commands:
```bash
cd /workspace/stable-diffusion-webui
python webui.py --listen --port 3000 --api --xformers
```

## Expected Costs
- **RTX A4000**: ~$0.30/hour
- **RTX 4070**: ~$0.40/hour  
- **RTX 4080**: ~$0.60/hour

## What You Get
✅ Full A1111 WebUI with all features  
✅ All major models pre-installed  
✅ API access for external tools  
✅ JupyterLab for advanced usage  
✅ Persistent storage for models/outputs  
✅ SSH access for customization  

## Troubleshooting
- **WebUI won't start**: Try the manual start commands above
- **Can't access**: Check firewall/ports in RunPod console
- **Slow generation**: Upgrade to RTX 4080
- **Out of memory**: Reduce batch size or image dimensions

## Alternative: Use Your Existing RunPod Endpoints
Your current RunPod endpoints work perfectly. You can:
1. Build a simple web UI that calls them
2. Use them directly via API
3. Integrate with other tools like ComfyUI Manager

Your endpoints:
- SD1.5: `https://api.runpod.ai/v2/b31v2rs4miedps`
- SDXL: `https://api.runpod.ai/v2/gjqjavs8kxe4ls`
- SD3: `https://api.runpod.ai/v2/2grk270njwwyjc`
- FLUX: `https://api.runpod.ai/v2/fyn1l6oonx8776`

## Recommendation
Since your RunPod deployment is already working perfectly, the **fastest path** is:
1. Deploy A1111 WebUI manually (5 minutes)
2. Keep your existing endpoints for API usage
3. Use A1111 for interactive web-based generation