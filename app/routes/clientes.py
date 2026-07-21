from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import verify_admin, verify_same_origin
from app.deps import get_db, templates
from app.models import Cliente

router = APIRouter(tags=["clientes"], dependencies=[Depends(verify_admin)])


@router.get("/clientes")
def lista_clientes(request: Request, q: str | None = None,
                   db: Session = Depends(get_db)):
    query = db.query(Cliente).order_by(Cliente.nome.asc())
    if q:
        like = f"%{q}%"
        query = query.filter(Cliente.nome.like(like) | Cliente.telefone.like(like))
    clientes = query.all()
    return templates.TemplateResponse(request, "clientes.html", {
        "clientes": clientes, "q": q or "",
    })


@router.post("/clientes")
def criar_cliente(
    nome: str = Form(...),
    telefone: str = Form(""),
    endereco: str = Form(""),
    email: str = Form(""),
    observacoes: str = Form(""),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_same_origin),
):
    if not nome.strip():
        return RedirectResponse("/clientes?erro=Nome+obrigatório", status_code=303)
    db.add(Cliente(
        nome=nome.strip(), telefone=telefone.strip() or None,
        endereco=endereco.strip() or None, email=email.strip() or None,
        observacoes=observacoes.strip() or None,
    ))
    db.commit()
    return RedirectResponse("/clientes?ok=Cliente+adicionado", status_code=303)


@router.get("/clientes/{cliente_id}/editar")
def editar_cliente(cliente_id: int, request: Request, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        return RedirectResponse("/clientes?erro=Não+encontrado", status_code=303)
    return templates.TemplateResponse(request, "cliente_editar.html", {"c": c})


@router.post("/clientes/{cliente_id}")
def atualizar_cliente(
    cliente_id: int,
    nome: str = Form(...),
    telefone: str = Form(""),
    endereco: str = Form(""),
    email: str = Form(""),
    observacoes: str = Form(""),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_same_origin),
):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        return RedirectResponse("/clientes?erro=Não+encontrado", status_code=303)
    c.nome = nome.strip()
    c.telefone = telefone.strip() or None
    c.endereco = endereco.strip() or None
    c.email = email.strip() or None
    c.observacoes = observacoes.strip() or None
    db.commit()
    return RedirectResponse("/clientes?ok=Cliente+atualizado", status_code=303)
