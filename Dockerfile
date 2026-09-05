FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY backend ./backend
COPY model ./model
COPY ml ./ml
COPY data ./data
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
