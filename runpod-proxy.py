#!/usr/bin/env python3
"""
RunPod Proxy Server for SwarmUI
Translates SwarmUI ComfyUI API calls to RunPod API calls
"""

import os
import json
import time
import logging
from flask import Flask, request, jsonify
import requests
from threading import Thread
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# RunPod configuration
RUNPOD_API_KEY = os.environ.get('RUNPOD_API_KEY')
if not RUNPOD_API_KEY:
    logger.error("RUNPOD_API_KEY not set")
    exit(1)

# Endpoint mappings
ENDPOINTS = {
    'sd15': 'https://api.runpod.ai/v2/b31v2rs4miedps',
    'sd2': 'https://api.runpod.ai/v2/jp1x3l4djxeut5', 
    'sdxl': 'https://api.runpod.ai/v2/gjqjavs8kxe4ls',
    'sd3': 'https://api.runpod.ai/v2/2grk270njwwyjc',
    'flux-schnell': 'https://api.runpod.ai/v2/fyn1l6oonx8776',
    'flux-dev': 'https://api.runpod.ai/v2/78mlef35sk73lu'
}

# Job tracking
active_jobs = {}

def translate_prompt_to_runpod(prompt_data):
    """Convert ComfyUI prompt to RunPod input format"""
    
    # Extract basic parameters from ComfyUI workflow
    text_prompt = "a beautiful landscape"  # Default
    negative_prompt = ""
    
    # Try to extract from workflow nodes
    if 'prompt' in prompt_data:
        workflow = prompt_data['prompt']
        for node_id, node in workflow.items():
            if node.get('class_type') == 'CLIPTextEncode':
                if 'text' in node.get('inputs', {}):
                    text_prompt = node['inputs']['text']
                    break
    
    return {
        'prompt': text_prompt,
        'negative_prompt': negative_prompt,
        'steps': 20,
        'cfg_scale': 7,
        'width': 512,
        'height': 512,
        'sampler_name': 'euler'
    }

@app.route('/object_info')
def object_info():
    """Return ComfyUI object info (simplified)"""
    return jsonify({
        "CheckpointLoaderSimple": {
            "input": {
                "required": {
                    "ckpt_name": ["MODEL", ]
                }
            },
            "output": ["MODEL", "CLIP", "VAE"],
            "output_is_list": [False, False, False],
            "output_name": ["MODEL", "CLIP", "VAE"],
            "name": "CheckpointLoaderSimple",
            "display_name": "Load Checkpoint",
            "description": "",
            "category": "loaders",
            "output_node": False
        }
    })

@app.route('/prompt', methods=['POST'])
def queue_prompt():
    """Queue a prompt (translate to RunPod)"""
    try:
        data = request.json
        client_id = request.args.get('client_id', str(uuid.uuid4()))
        
        # Translate prompt to RunPod format
        runpod_input = translate_prompt_to_runpod(data)
        
        # Use SD1.5 endpoint for now (you can add model selection logic)
        model_type = 'sd15'  # Default model
        endpoint_url = ENDPOINTS[model_type]
        
        # Submit to RunPod
        response = requests.post(
            f"{endpoint_url}/run",
            headers={
                'Authorization': f'Bearer {RUNPOD_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={'input': runpod_input}
        )
        
        if response.status_code == 200:
            runpod_result = response.json()
            job_id = runpod_result.get('id')
            
            if job_id:
                # Store job mapping
                prompt_id = str(uuid.uuid4())
                active_jobs[prompt_id] = {
                    'runpod_job_id': job_id,
                    'endpoint_url': endpoint_url,
                    'client_id': client_id,
                    'status': 'queued'
                }
                
                return jsonify({
                    'prompt_id': prompt_id,
                    'number': 1,
                    'node_errors': {}
                })
        
        return jsonify({'error': 'Failed to queue prompt'}), 500
        
    except Exception as e:
        logger.error(f"Error queuing prompt: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/history/<prompt_id>')
def get_history(prompt_id):
    """Get job history/status"""
    try:
        if prompt_id not in active_jobs:
            return jsonify({})
        
        job_info = active_jobs[prompt_id]
        runpod_job_id = job_info['runpod_job_id']
        endpoint_url = job_info['endpoint_url']
        
        # Check RunPod status
        response = requests.get(
            f"{endpoint_url}/status/{runpod_job_id}",
            headers={'Authorization': f'Bearer {RUNPOD_API_KEY}'}
        )
        
        if response.status_code == 200:
            runpod_status = response.json()
            
            if runpod_status.get('status') == 'COMPLETED':
                # Return completed job with fake image data
                return jsonify({
                    prompt_id: {
                        'prompt': [1, {}, {}],
                        'outputs': {
                            '1': {
                                'images': [{
                                    'filename': 'generated_image.png',
                                    'subfolder': '',
                                    'type': 'output'
                                }]
                            }
                        },
                        'status': {
                            'status_str': 'success',
                            'completed': True,
                            'messages': []
                        }
                    }
                })
        
        return jsonify({})
        
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({})

@app.route('/view')
def view_image():
    """Serve generated image"""
    # For now, return a placeholder
    return "Image would be here", 200, {'Content-Type': 'image/png'}

@app.route('/ws')
def websocket():
    """WebSocket endpoint (not implemented)"""
    return jsonify({'error': 'WebSocket not supported'}), 501

if __name__ == '__main__':
    logger.info("Starting RunPod Proxy Server...")
    logger.info(f"Configured endpoints: {list(ENDPOINTS.keys())}")
    app.run(host='0.0.0.0', port=8188, debug=False)