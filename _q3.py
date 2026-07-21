import sqlite3
c=sqlite3.connect('database/avs.db')
print("equip count", c.execute("select count(*) from equipamentos").fetchone()[0])
print("cliente count", c.execute("select count(*) from clientes").fetchone()[0])
print("ordem2 equip", c.execute("select equipamento_id,total_centavos from ordens where id=2").fetchone())
