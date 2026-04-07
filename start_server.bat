@echo off
REM Start FastAPI server with uvicorn using venv Python
cd /d %~dp0
venv\Scripts\python.exe -m uvicorn web.app:app --reload --host 0.0.0.0 --port 8000