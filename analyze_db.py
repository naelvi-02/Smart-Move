"""Deep analysis of hidden models."""
import requests, asyncio, httpx, sys, re
sys.path.insert(0, "backend")
from config import get_settings

BASE = "https://api.naelvi.com/api/models"

# Analysis 1: Why 404 models hidden?
# UI filter: nsfw_flag == True AND available_in_novita == True
# Novita API total: 1084 | Visible in UI: 680 | Gap: 404
# From /api/models sample: 41% nsfw, 59% sfw => ~549 SFW models get filtered out
# But we also saw from Novita API: nsfw=535, sfw=549 => 535 NSFW
# Visible = 680 (535 novita + some civitai deduped)

print("=== WHY 404 MODELS HIDDEN ===")
print("Total Novita in API: 1084")
print("Novita NSFW: 535")
print("Novita SFW: 549")
print("UI filter requires nsfw_flag=True => 549 SFW models hidden")
print("Visible Novita: 535 (matches!)")
print("")

# Analysis 2: in_whitelist check
async def check_whitelist():
    settings = get_settings()
    wl_nsfw = 0
    wl_sfw = 0
    nwl_nsfw = 0
    nwl_sfw = 0
    not_usable_examples = []
    cursor = None
    
    async with httpx.AsyncClient(timeout=30) as c:
        while True:
            params = {'filter.types': 'checkpoint', 'pagination.limit': '100'}
            if cursor:
                params['pagination.cursor'] = cursor
            res = await c.get(f'{settings.novita_base_url}/model', 
                            headers={'Authorization': f'Bearer {settings.novita_api_key}'}, 
                            params=params)
            data = res.json()
            models = data.get('models', [])
            
            for m in models:
                wl = m.get('in_whitelist', False)
                nsfw = m.get('is_nsfw', False)
                if wl and nsfw:
                    wl_nsfw += 1
                elif wl and not nsfw:
                    wl_sfw += 1
                elif not wl and nsfw:
                    nwl_nsfw += 1
                    if len(not_usable_examples) < 5:
                        not_usable_examples.append(m.get('model_name', m.get('name', '???')))
                else:
                    nwl_sfw += 1
            
            cursor = data.get('pagination', {}).get('next_cursor')
            if not cursor or not models:
                break
    
    print("=== WHITELIST ANALYSIS ===")
    print(f"Whitelisted + NSFW: {wl_nsfw}")
    print(f"Whitelisted + SFW: {wl_sfw}")
    print(f"Not whitelisted + NSFW: {nwl_nsfw}")
    print(f"Not whitelisted + SFW: {nwl_sfw}")
    print(f"\nExamples of NOT whitelisted but NSFW: {not_usable_examples}")

asyncio.run(check_whitelist())

# Analysis 3: What percentage of models have civitai enrichment?
async def check_enrichment():
    settings = get_settings()
    enriched = 0
    not_enriched = 0
    cursor = None
    
    async with httpx.AsyncClient(timeout=30) as c:
        while True:
            params = {'filter.types': 'checkpoint', 'pagination.limit': '100'}
            if cursor:
                params['pagination.cursor'] = cursor
            res = await c.get(f'{settings.novita_base_url}/model', 
                            headers={'Authorization': f'Bearer {settings.novita_api_key}'}, 
                            params=params)
            data = res.json()
            models = data.get('models', [])
            
            for m in models:
                sd_name = m.get('sd_name', '')
                match = re.search(r'_(\d+)\.safetensors', sd_name)
                has_version_id = m.get('civitai_version_id')
                if (match and len(match.group(1)) >= 4) or has_version_id:
                    enriched += 1
                else:
                    not_enriched += 1
            
            cursor = data.get('pagination', {}).get('next_cursor')
            if not cursor or not models:
                break
    
    print(f"\n=== ENRICHMENT POTENTIAL ===")
    print(f"Has Civitai version ID (extractable): {enriched}")
    print(f"No Civitai version ID: {not_enriched}")

asyncio.run(check_enrichment())
