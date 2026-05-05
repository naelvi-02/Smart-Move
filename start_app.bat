@echo off
echo Starting Smart Move App...

:: Start Backend
start "Smart Move Backend" cmd /k "cd backend && uvicorn main:app --reload"

:: Start Frontend
start "Smart Move Frontend" cmd /k "cd frontend && npm run dev"

echo Backend running on http://localhost:8000
echo Frontend running on http://localhost:3000
echo.
echo Servers started in separate windows!
pause
