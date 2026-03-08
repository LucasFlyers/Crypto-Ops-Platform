web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: celery -A app.workers.celery_app worker --loglevel=info --queues=classification,fraud,routing --concurrency=2
dashboard: streamlit run dashboard/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
