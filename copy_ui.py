import os

source_file = "Premium SaaS Admin Dashboard/src/app/App.tsx"
target_file = "frontend/src/app/admin/page.tsx"

with open(source_file, "r", encoding="utf-8") as f:
    content = f.read()

with open(target_file, "w", encoding="utf-8") as f:
    f.write('"use client";\n' + content)

print("Copied successfully!")
