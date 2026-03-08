@echo off
echo ========================================
echo  Crypto Ops Platform - Local Setup
echo ========================================

echo.
echo [1/4] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

echo.
echo [2/4] Installing dependencies...
pip install fastapi==0.111.0 uvicorn[standard]==0.29.0 sqlalchemy[asyncio]==2.0.30 asyncpg==0.29.0 alembic==1.13.1 pydantic==2.7.1 pydantic-settings==2.2.1 celery[redis]==5.4.0 redis==5.0.4 openai==1.35.0 structlog==24.2.0 httpx==0.27.0 tenacity==8.3.0 python-dotenv==1.0.1 streamlit==1.35.0 pandas==2.2.2 plotly==5.22.0 psycopg2-binary==2.9.9

echo.
echo [3/4] Running database migrations...
alembic upgrade head

echo.
echo [4/4] Setup complete!
echo.
echo ========================================
echo  To start the platform, run: start.bat
echo ========================================
pause
