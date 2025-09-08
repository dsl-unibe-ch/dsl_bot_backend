FROM python:3.12.11-slim

WORKDIR /app

RUN pip install uv==0.8.14

COPY pyproject.toml .
COPY app ./app

RUN uv pip install -r pyproject.toml --system

EXPOSE 8000

CMD ["uvicorn", "app.api.v1.routers.main:app", "--host", "0.0.0.0", "--port", "8000"]