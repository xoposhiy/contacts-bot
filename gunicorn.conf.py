# Gunicorn configuration to run FastAPI (ASGI) correctly when Gunicorn is used.
# This ensures Gunicorn uses Uvicorn's ASGI worker instead of the default WSGI sync worker.

worker_class = "uvicorn.workers.UvicornWorker"
