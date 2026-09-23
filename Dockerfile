FROM python:3.14.7-slim

WORKDIR /app

RUN pip install uv==0.8.14

COPY pyproject.toml .
COPY README.md .
COPY app ./app

RUN uv pip install . --system

COPY customer_config ./customer_config
COPY scripts/kafka_to_azure_consumer.py ./scripts/kafka_to_azure_consumer.py

EXPOSE 8000

CMD ["uvicorn", "app.api.v1.routers.main:app", "--host", "0.0.0.0", "--port", "8000"]