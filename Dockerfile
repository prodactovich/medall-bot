FROM python:3.11-slim

WORKDIR /app

# Ставим зависимости отдельно, чтобы реже пересобирать слои
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем только runtime-части проекта
COPY alembic.ini .
COPY migrations ./migrations
COPY src ./src
COPY domain ./domain

# Применяем миграции и запускаем бота (polling)
CMD ["sh", "-c", "python -m alembic upgrade head && python -m src.bot"]
