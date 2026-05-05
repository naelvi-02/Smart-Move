import sqlite3
conn = sqlite3.connect('smart_move.db')
c = conn.cursor()
print("--- Total Realistic Models ---")
c.execute("SELECT source, count(*) FROM models WHERE style_bucket='realistic_human' GROUP BY source")
print(c.fetchall())
conn.close()
