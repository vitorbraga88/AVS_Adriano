@echo off
set ADMIN_PASSWORD=teste
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8090 %*
