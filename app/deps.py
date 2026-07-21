from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.database import SessionLocal

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def brl(valor) -> str:
    """Decimal/float para R$ X,XX"""
    try:
        return f"R$ {float(valor):.2f}".replace(".", ",")
    except Exception:
        return "R$ -"


def brl_c(centavos: int) -> str:
    """Centavos inteiros para R$ X,XX"""
    try:
        return f"R$ {centavos / 100:.2f}".replace(".", ",")
    except Exception:
        return "R$ -"


templates.env.filters["brl"] = brl
templates.env.filters["brl_c"] = brl_c


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
