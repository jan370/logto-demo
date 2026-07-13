FROM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/jan370/logto-demo"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "--timeout", "30", "app:app"]
