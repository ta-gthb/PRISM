FROM python:3.11-slim

# Install system dependencies (Tesseract OCR, language data, OpenCV runtime libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --root-user-action=ignore --default-timeout=100 --retries 5 -r requirements.txt

# Copy backend code
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    TESSERACT_CMD=/usr/bin/tesseract

EXPOSE 8000

# Run schema init and start Uvicorn
CMD ["sh", "-c", "python -m db.init_db && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
