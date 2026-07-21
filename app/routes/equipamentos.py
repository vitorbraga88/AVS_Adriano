from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import verify_admin, verify_same_origin
from app.deps import get_db, templates
from app.models import Cliente, Equipamento

router = APIRouter(tags=["equipamentos"], dependencies=[Depends(verify_admin)])


@router.get("/equipamentos")
def lista_equipamentos(request: Request, cliente_id: int | None = None,
                       db: Session = Depends(get_db)):
    query = (db.query(Equipamento).options(joinedload(Equipamento.cliente))
             .order_by(Equipamento.created_at.desc()))
    if cliente_id:
        query = query.filter(Equipamento.cliente_id == cliente_id)
    equipamentos = query.all()
    clientes = db.query(Cliente).order_by(Cliente.nome.asc()).all()
    return templates.TemplateResponse(request, "equipamentos.html", {
        "equipamentos": equipamentos, "clientes": clientes,
        "cliente_id": cliente_id,
    })


@router.post("/equipamentos")
def criar_equipamento(
    cliente_id: int = Form(...),
    descricao: str = Form(""),
    marca: str = Form(""),
    modelo: str = Form(""),
    numero_serie: str = Form(""),
    patrimonio: str = Form(""),
    observacoes: str = Form(""),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_same_origin),
):
    if not db.query(Cliente).filter(Cliente.id == cliente_id).first():
        return RedirectResponse("/equipamentos?erro=Cliente+inválido", status_code=303)
    db.add(Equipamento(
        cliente_id=cliente_id, descricao=descricao.strip() or None,
        marca=marca.strip() or None, modelo=modelo.strip() or None,
        numero_serie=numero_serie.strip() or None,
        patrimonio=patrimonio.strip() or None,
        observacoes=observacoes.strip() or None,
    ))
    db.commit()
    return RedirectResponse("/equipamentos?ok=Equipamento+adicionado", status_code=303)


@router.get("/equipamentos/{eq_id}/editar")
def editar_equipamento(eq_id: int, request: Request, db: Session = Depends(get_db)):
    eq = db.query(Equipamento).filter(Equipamento.id == eq_id).first()
    if not eq:
        return RedirectResponse("/equipamentos?erro=Não+encontrado", status_code=303)
    clientes = db.query(Cliente).order_by(Cliente.nome.asc()).all()
    return templates.TemplateResponse(request, "equipamento_editar.html", {
        "e": eq, "clientes": clientes,
    })


@router.post("/equipamentos/{eq_id}")
def atualizar_equipamento(
    eq_id: int,
    cliente_id: int = Form(...),
    descricao: str = Form(""),
    marca: str = Form(""),
    modelo: str = Form(""),
    numero_serie: str = Form(""),
    patrimonio: str = Form(""),
    observacoes: str = Form(""),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_same_origin),
):
    eq = db.query(Equipamento).filter(Equipamento.id == eq_id).first()
    if not eq:
        return RedirectResponse("/equipamentos?erro=Não+encontrado", status_code=303)
    eq.cliente_id = cliente_id
    eq.descricao = descricao.strip() or None
    eq.marca = marca.strip() or None
    eq.modelo = modelo.strip() or None
    eq.numero_serie = numero_serie.strip() or None
    eq.patrimonio = patrimonio.strip() or None
    eq.observacoes = observacoes.strip() or None
    db.commit()
    return RedirectResponse("/equipamentos?ok=Equipamento+atualizado", status_code=303)


@router.post("/equipamentos/{eq_id}/excluir")
def excluir_equipamento(eq_id: int, db: Session = Depends(get_db),
                        _csrf: None = Depends(verify_same_origin)):
    eq = db.query(Equipamento).filter(Equipamento.id == eq_id).first()
    if not eq:
        return RedirectResponse("/equipamentos?erro=Não+encontrado", status_code=303)
    db.delete(eq)
    db.commit()
    return RedirectResponse("/equipamentos?ok=Equipamento+excluído", status_code=303)
