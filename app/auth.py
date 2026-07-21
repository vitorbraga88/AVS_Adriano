import os
import secrets
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic(auto_error=False)


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    pwd = os.getenv("ADMIN_PASSWORD", "")
    if not pwd:
        # Sem senha configurada: só libera em dev explícito (AVS_DEV=1).
        # AVS_DEV=1 desativa TODA autenticação desta rota (qualquer origem é
        # tratada como admin). SÓ em .env de desenvolvimento local; NUNCA em
        # produção nem em .env exposto/publicado.
        if os.getenv("AVS_DEV") == "1":
            return "dev"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_PASSWORD não configurado no servidor",
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária",
            headers={"WWW-Authenticate": "Basic"},
        )
    ok_user = secrets.compare_digest(credentials.username.encode(), b"admin")
    ok_pass = secrets.compare_digest(credentials.password.encode(), pwd.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def verify_same_origin(request: Request) -> None:
    """Mitigação de CSRF para os formulários HTML protegidos só por Basic Auth.

    Sem sessão/cookie, o navegador re-envia as credenciais Basic cacheadas
    para a mesma origem em qualquer requisição. Para POSTs de formulário
    navegado por humano, exigimos que Origin (ou Referer) aponte para o
    mesmo host da requisição. NÃO usar em /api/* — são chamadas
    servidor-a-servidor (n8n / JS do form) sem credencial ambiente a explorar.
    """
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requisição rejeitada: cabeçalho Origin/Referer ausente",
        )
    origin_host = urlparse(origin).netloc
    request_host = request.headers.get("host", "")
    if not origin_host or origin_host != request_host:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requisição rejeitada: origem cruzada não permitida",
        )
