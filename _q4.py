import sqlite3; c=sqlite3.connect('database/avs.db'); c.row_factory=sqlite3.Row
o=dict(c.execute("select numero,status,total_centavos from ordens where id=4").fetchone())
print("ORDEM4", o)
