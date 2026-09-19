FROM python:3.11-slim

# Install system dependencies (PaddleOCR deep learning runtime, libgomp1, OpenCV, Tesseract OCR fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt ./requirements.txt
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --root-user-action=ignore --default-timeout=100 --retries 5 -r requirements.txt

# Copy backend code
COPY backend/ .

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    TESSERACT_CMD=/usr/bin/tesseract

EXPOSE 8000

# Run schema init and start Uvicorn
CMD ["sh", "-c", "python -m db.init_db && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
