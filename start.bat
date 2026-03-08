@echo off
echo ========================================
echo  Starting Crypto Ops Platform
echo ========================================

call venv\Scripts\activate

echo.
echo Starting FastAPI backend...
start "API Server" cmd /k "call venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo Starting Celery worker...
start "Celery Worker" cmd /k "call venv\Scripts\activate && celery -A app.workers.celery_app worker --loglevel=info --queues=classification,fraud,routing --concurrency=2 --pool=solo"

timeout /t 3 /nobreak >nul

echo Starting Streamlit dashboard...
start "Dashboard" cmd /k "call venv\Scripts\activate && streamlit run dashboard/app.py --server.port=8501"

echo.
echo ========================================
echo  All services started!
echo.
echo  API:       http://localhost:8000
echo  API Docs:  http://localhost:8000/docs
echo  Dashboard: http://localhost:8501
echo ========================================
echo.
pause
