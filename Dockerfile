FROM python:3.12-slim

WORKDIR /app

# Install deps first for layer caching
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction

COPY . .

EXPOSE 5000

# MONGO_URI / OPENROUTER_API_KEY come from the env. Seed once separately:
#   docker run --env-file .env cruzaid python setup_data.py
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
