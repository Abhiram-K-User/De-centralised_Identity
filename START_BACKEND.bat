@echo off
echo ================================================================================
echo                     STARTING BACKEND SERVER
echo ================================================================================
echo.

cd "C:\Users\sh\Downloads\sem 3\main el sem 3\Block Chain Optimization\De-centralised_Identity"

echo [*] Starting FastAPI backend on http://localhost:8000
echo [*] API Documentation will be available at http://localhost:8000/api/docs
echo.
echo Press Ctrl+C to stop the server
echo.

python app\main.py

pause

