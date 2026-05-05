import sqlite3
conn = sqlite3.connect('smart_move.db')
c = conn.cursor()
print("--- Breakdown of Available Models ---")
c.execute("SELECT source, count(*) FROM models WHERE available_in_novita=1 GROUP BY source")
print(c.fetchall())

print("\n--- Breakdown of Available Models (Realistic) ---")
c.execute("SELECT source, count(*) FROM models WHERE available_in_novita=1 AND style_bucket='realistic_human' GROUP BY source")
print(c.fetchall())
conn.close()
