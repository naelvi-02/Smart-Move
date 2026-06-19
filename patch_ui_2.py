import re

file_path = "frontend/src/app/admin/page.tsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix auto-scroll
content = content.replace(
    "logsEndRef.current?.scrollIntoView({ behavior: \"smooth\" });",
    "if (logs.length > 0) logsEndRef.current?.scrollIntoView({ behavior: \"smooth\" });"
)

# 2. Change Smart Move Branding
content = content.replace(
    '<h1 className="text-white font-semibold leading-tight">Smart Move</h1>',
    '<h1 className="text-white font-semibold leading-tight">Mass Scraper</h1>'
)
content = content.replace(
    '<p className="text-[10px] text-zinc-500 font-mono tracking-wider">INTELLIGENCE</p>',
    '<p className="text-[10px] text-zinc-500 font-mono tracking-wider">WEB TOOL</p>'
)

# 3. Remove Sidebar Links (LLM Explorer, Image Models, Benchmarks, Cost Simulator)
sidebar_links_pattern = r'<SidebarItem icon=\{<Box className="w-4 h-4" />\} label="LLM Explorer" />.*?<SidebarItem icon=\{<Calculator className="w-4 h-4" />\} label="Cost Simulator" />'
content = re.sub(sidebar_links_pattern, "", content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("UI patched successfully")
