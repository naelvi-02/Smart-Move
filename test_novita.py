import asyncio, httpx, time
import sys
sys.path.insert(0, "backend")
from config import get_settings

async def test_generation():
    settings = get_settings()
    url = f"{settings.novita_base_url}/async/txt2img"
    headers = {
        "Authorization": f"Bearer {settings.novita_api_key}",
        "Content-Type": "application/json"
    }
    
    # Let's test a few NSFW models from our previous analysis
    models_to_test = [
        "meinahentai_v4_70340.safetensors",
        "pornmasterPro_fullV5-inpainting_135217.safetensors", 
        "dreamshaper_8_93211.safetensors"
    ]
    
    async with httpx.AsyncClient(timeout=30) as c:
        for model in models_to_test:
            payload = {
                "extra": {
                    "response_image_type": "jpeg",
                    "enable_nsfw_detection": False
                },
                "request": {
                    "model_name": model,
                    "prompt": "a beautiful woman, highly detailed",
                    "negative_prompt": "ugly, blurry",
                    "width": 512,
                    "height": 512,
                    "image_num": 1,
                    "steps": 20,
                    "seed": 123,
                    "clip_skip": 1,
                    "guidance_scale": 7.5,
                    "sampler_name": "Euler a"
                }
            }
            
            print(f"Testing model: {model}")
            res = await c.post(url, headers=headers, json=payload)
            print(f"Status: {res.status_code}")
            print(f"Response: {res.text}")
            
            if res.status_code == 200:
                task_id = res.json().get("task_id")
                if task_id:
                    print(f"Task started: {task_id}")
                    # Don't wait for completion, just verifying if it's ACCEPTED

asyncio.run(test_generation())
