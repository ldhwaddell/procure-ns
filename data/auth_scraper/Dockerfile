FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

WORKDIR /app

RUN pip install --no-cache-dir playwright

COPY . .

ENTRYPOINT ["python", "main.py"]
