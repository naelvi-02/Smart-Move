import sqlite3
conn = sqlite3.connect('smart_move.db')
c = conn.cursor()
c.execute("SELECT source, count(*), sum(available_in_novita) FROM models GROUP BY source")
print(c.fetchall())
conn.close()
