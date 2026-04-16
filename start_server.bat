@echo off
REM Start FastAPI server with uvicorn using venv Python
cd /d %~dp0

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Start the FastAPI server
python -m uvicorn web.app:app --reload --host 0.0.0.0 --port 8000