
FROM python:3.11-slim

# Install only the packages needed by the ETL worker.
COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir \
    -r /tmp/requirements.txt \
    && useradd --create-home --uid 10001 worker

WORKDIR /app

COPY worker.py /app/worker.py

# Run as a non-root user.
USER worker

ENTRYPOINT ["python", "/app/worker.py"]