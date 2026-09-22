FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir . \
    && addgroup --system mosala \
    && adduser --system --ingroup mosala --home /nonexistent --no-create-home mosala \
    && chown -R mosala:mosala /app

USER mosala

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
