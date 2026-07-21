import sqlite3
c=sqlite3.connect('database/avs.db'); c.row_factory=sqlite3.Row
o=c.execute("select id,numero,status,total_centavos,equipamento_id,cliente_id from ordens").fetchall()
for r in o: print("ORDEM", dict(r))
print("ITENS", [dict(r) for r in c.execute("select descricao,quantidade,preco_centavos from ordem_itens")])
print("EQUIP", [dict(r) for r in c.execute("select id,cliente_id,descricao,numero_serie from equipamentos")])
