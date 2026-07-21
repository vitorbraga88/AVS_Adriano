import sqlite3
c=sqlite3.connect('database/avs.db'); c.row_factory=sqlite3.Row
print("VENDAS", [dict(r) for r in c.execute("select ordem_id,valor_centavos,custo_centavos,data_venda from financeiro_vendas")])
print("ORDEM1", dict(c.execute("select status,data_recebimento,data_conclusao,data_servico from ordens where id=1").fetchone()))
