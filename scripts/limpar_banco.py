"""Limpa todos os dados do banco AVS mantendo a estrutura (schema).

Uso:
    python -m scripts.limpar_banco               # faz backup e limpa
    python -m scripts.limpar_banco --sem-backup   # pula o backup (não recomendado)

Copia database/avs.db para database/backups/avs_<timestamp>.db antes de
apagar os dados (a menos que --sem-backup seja passado). Não altera o
schema — apenas esvazia as tabelas (DELETE, na ordem que respeita as FKs);
o app volta a funcionar normalmente no próximo request, sem cadastros.
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import DB_PATH, engine  # noqa: E402

# Ordem de limpeza respeita as FKs (tabelas filhas antes das tabelas-pai).
TABELAS_EM_ORDEM = [
    "notificacoes",
    "financeiro_vendas",
    "ordem_custos",
    "ordem_itens",
    "ordens",
    "equipamentos",
    "clientes",
    "financeiro_despesas",
    "assinaturas",
    "sugestoes",
]


def backup() -> Path:
    dest_dir = DB_PATH.parent / "backups"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"avs_{datetime.now():%Y%m%d_%H%M%S}.db"
    shutil.copy2(DB_PATH, dest)
    return dest


def limpar() -> None:
    with engine.begin() as conn:
        for tabela in TABELAS_EM_ORDEM:
            conn.execute(text(f"DELETE FROM {tabela}"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sem-backup", action="store_true",
                    help="pula o backup automático (não recomendado)")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"Banco não encontrado em {DB_PATH}; nada a limpar.")
        return

    if not args.sem_backup:
        dest = backup()
        print(f"Backup salvo em {dest}")

    limpar()
    print("Dados removidos. Estrutura (schema) preservada — o app segue funcionando normalmente.")


if __name__ == "__main__":
    main()
