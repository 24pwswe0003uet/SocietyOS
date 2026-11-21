FROM python:3.13-slim

WORKDIR /app

# System deps for weasyprint, pdfplumber, etc
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations then start
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]

EXPOSE 8000
