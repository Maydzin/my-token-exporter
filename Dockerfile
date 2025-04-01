FROM python:3.10-slim

WORKDIR /app

COPY gitlab-token-exporter/ .

RUN pip install --no-cache-dir prometheus_client requests

CMD ["python", "gitlab-token-exporter.py"]