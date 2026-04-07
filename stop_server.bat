@echo off
REM Stop all uvicorn processes (Windows only)
taskkill /F /IM uvicorn.exe >nul 2>&1
