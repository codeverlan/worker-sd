# Multi-Model ComfyUI RunPod Worker
# Supports SD1.5, SD2, SDXL, SD3, FLUX, and other variants

FROM runpod/pytorch:2.2.1-py3.11-cuda12.1.1-devel-ubuntu22.04

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Set working directory
WORKDIR /

# Update and install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    git \
    python3-venv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && \
    pip install -r requirements.txt

# Install additional dependencies for all model types
RUN pip install \
    accelerate \
    transformers \
    diffusers \
    opencv-python \
    Pillow \
    runpod \
    requests \
    boto3

# Install ComfyUI Manager for custom nodes
RUN cd ComfyUI/custom_nodes && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# Install essential custom nodes for broader compatibility
RUN cd ComfyUI/custom_nodes && \
    git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git && \
    git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git && \
    git clone https://github.com/WASasquatch/was-node-suite-comfyui.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git

# Create model directories
RUN mkdir -p /ComfyUI/models/checkpoints && \
    mkdir -p /ComfyUI/models/vae && \
    mkdir -p /ComfyUI/models/loras && \
    mkdir -p /ComfyUI/models/controlnet && \
    mkdir -p /ComfyUI/models/clip && \
    mkdir -p /ComfyUI/models/embeddings && \
    mkdir -p /ComfyUI/models/upscale_models

# Copy the worker script
COPY src/ /

# Install dependencies for the worker
RUN pip install -r requirements.txt

# Expose ComfyUI port
EXPOSE 8188

# Set the default command
CMD python -u /rp_handler.py