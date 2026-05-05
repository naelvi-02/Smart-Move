import sqlite3
c = sqlite3.connect('smart_move.db').cursor()
c.execute("SELECT source, COUNT(*) FROM models WHERE type='image' GROUP BY source")
print(c.fetchall())
c.execute("SELECT COUNT(*) FROM models WHERE type='image'")
print("Total:", c.fetchone()[0])
