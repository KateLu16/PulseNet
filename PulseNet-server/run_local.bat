@echo off
REM Chay PulseNet LOCAL tren may Windows (backend + mo web)
REM Gateway BLE chi chay tren Pi - tai day chi test dashboard/backend.

cd /d %~dp0backend

echo [PulseNet] Dang khoi dong backend tai http://127.0.0.1:8000/ ...
start "PulseNet Backend" .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

timeout /t 4 /nobreak >nul
start http://127.0.0.1:8000/

echo [PulseNet] Backend dang chay (cua so rieng). Dung bang cach dong cua so do.
