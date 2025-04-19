FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

WORKDIR /app

RUN pip install --no-cache-dir playwright

COPY . .

ENTRYPOINT ["python", "main.py"]

