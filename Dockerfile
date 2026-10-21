FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY mock_mcp ./mock_mcp

EXPOSE 8080 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
