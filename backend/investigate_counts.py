import sqlite3
import re

def normalize(name):
    if not name: return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())

conn = sqlite3.connect('smart_move.db')
c = conn.cursor()

# Check raw count
c.execute("SELECT count(*) FROM models WHERE source='novita' AND type='image'")
total_count = c.fetchone()[0]

# Check names
c.execute("SELECT name FROM models WHERE source='novita' AND type='image'")
rows = c.fetchall()

unique_names = set()
normalized_unique = set()

for r in rows:
    name = r[0]
    if name:
        unique_names.add(name)
        normalized_unique.add(normalize(name))

print(f"Total Novita Rows: {total_count}")
print(f"Unique Exact Names: {len(unique_names)}")
print(f"Unique Normalized Names: {len(normalized_unique)}")

conn.close()
