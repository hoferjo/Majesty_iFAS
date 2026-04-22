@echo off
REM Stop uvicorn processes (including `python -m uvicorn web.app:app`)
taskkill /F /IM uvicorn.exe >nul 2>&1

REM Kill python processes that run this app via uvicorn.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'python\s+-m\s+uvicorn\s+web\.app:app' -or $_.CommandLine -match 'uvicorn\s+web\.app:app' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

REM Fallback: kill anything still listening on port 8000.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":8000 .*LISTENING"') do taskkill /F /PID %%p >nul 2>&1
