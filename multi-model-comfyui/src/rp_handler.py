#!/usr/bin/env python3
"""
RunPod Worker Handler for Multi-Model ComfyUI
Supports SD1.5, SD2, SDXL, SD3, FLUX, and other variants
"""

import os
import json
import base64
import requests
import runpod
import time
import subprocess
import threading
from io import BytesIO
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ComfyUI configuration
COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_DIR = "/ComfyUI"

# Global ComfyUI process
comfyui_process = None

def start_comfyui():
    """Start ComfyUI server"""
    global comfyui_process
    logger.info("Starting ComfyUI server...")
    
    os.chdir(COMFYUI_DIR)
    comfyui_process = subprocess.Popen([
        "python", "main.py", 
        "--listen", "0.0.0.0", 
        "--port", "8188",
        "--dont-print-server"
    ])
    
    # Wait for ComfyUI to be ready
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
            if response.status_code == 200:
                logger.info("ComfyUI server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        logger.info(f"Waiting for ComfyUI to start... (attempt {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    logger.error("Failed to start ComfyUI server")
    return False

def get_model_workflow(model_type, prompt, negative_prompt="", steps=25, cfg=7, width=512, height=512, sampler="euler", scheduler="normal"):
    """Generate ComfyUI workflow based on model type"""
    
    # Base workflow template
    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": "model.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "2": {
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "4": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "5": {
            "inputs": {
                "seed": -1,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0]
            },
            "class_type": "KSampler"
        },
        "6": {
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2]
            },
            "class_type": "VAEDecode"
        },
        "7": {
            "inputs": {
                "filename_prefix": "RunPod_",
                "images": ["6", 0]
            },
            "class_type": "SaveImage"
        }
    }
    
    # Adjust workflow based on model type
    if model_type.upper() in ["SDXL", "SD3", "FLUX"]:
        # These models typically use higher resolutions
        workflow["4"]["inputs"]["width"] = max(width, 1024)
        workflow["4"]["inputs"]["height"] = max(height, 1024)
    
    return workflow

def queue_prompt(workflow):
    """Queue a prompt to ComfyUI"""
    try:
        response = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error queuing prompt: {e}")
        return None

def get_image_result(prompt_id):
    """Get the generated image result"""
    max_attempts = 120  # 2 minutes timeout
    
    for attempt in range(max_attempts):
        try:
            # Check if job is complete
            history_response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
            history_response.raise_for_status()
            history = history_response.json()
            
            if prompt_id in history:
                # Job is complete, get the image
                outputs = history[prompt_id]["outputs"]
                
                # Find the SaveImage node output
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        for image_info in node_output["images"]:
                            filename = image_info["filename"]
                            subfolder = image_info.get("subfolder", "")
                            
                            # Get the image
                            image_response = requests.get(
                                f"{COMFYUI_URL}/view",
                                params={"filename": filename, "subfolder": subfolder}
                            )
                            image_response.raise_for_status()
                            
                            # Convert to base64
                            image_base64 = base64.b64encode(image_response.content).decode('utf-8')
                            return image_base64
            
        except Exception as e:
            logger.error(f"Error getting image result: {e}")
        
        time.sleep(1)
    
    return None

def handler(job):
    """Main handler function for RunPod jobs"""
    try:
        job_input = job.get("input", {})
        
        # Extract parameters
        prompt = job_input.get("prompt", "a beautiful landscape")
        negative_prompt = job_input.get("negative_prompt", "")
        model_type = job_input.get("model_type", "SD15")
        steps = job_input.get("steps", 25)
        cfg = job_input.get("cfg_scale", 7)
        width = job_input.get("width", 512)
        height = job_input.get("height", 512)
        sampler = job_input.get("sampler_name", "euler")
        scheduler = job_input.get("scheduler", "normal")
        
        logger.info(f"Processing job with model_type: {model_type}, prompt: {prompt[:100]}...")
        
        # Generate workflow
        workflow = get_model_workflow(
            model_type=model_type,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg=cfg,
            width=width,
            height=height,
            sampler=sampler,
            scheduler=scheduler
        )
        
        # Queue the prompt
        queue_result = queue_prompt(workflow)
        if not queue_result:
            return {"error": "Failed to queue prompt"}
        
        prompt_id = queue_result["prompt_id"]
        logger.info(f"Queued prompt with ID: {prompt_id}")
        
        # Get the result
        image_base64 = get_image_result(prompt_id)
        if not image_base64:
            return {"error": "Failed to generate image"}
        
        return {
            "status": "success",
            "image": image_base64,
            "prompt_id": prompt_id,
            "model_type": model_type
        }
        
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {"error": str(e)}

def main():
    """Main function to start the worker"""
    # Start ComfyUI in the background
    comfyui_thread = threading.Thread(target=start_comfyui)
    comfyui_thread.daemon = True
    comfyui_thread.start()
    
    # Wait for ComfyUI to be ready
    if not start_comfyui():
        logger.error("Failed to start ComfyUI, exiting...")
        return
    
    # Start the RunPod worker
    logger.info("Starting RunPod worker...")
    runpod.serverless.start({"handler": handler})

if __name__ == "__main__":
    main()