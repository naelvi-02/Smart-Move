import requests
res = requests.get('https://api.naelvi.com/api/models/image?limit=100&search=UnstableDiffusers')
data = res.json()
print('Found:', data.get('total'))
for m in data.get('models', []):
    name = m['name'].encode('ascii', 'ignore').decode('ascii')
    print(f"{name} | source: {m['source']} | id: {m['model_id']} | novita_available: {m['available_in_novita']}")
