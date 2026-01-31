FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY bot/ ./bot/
COPY run.py .

# Создание директории для данных
RUN mkdir -p /app/data

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:///data/claude_bot.db

# Запуск бота
CMD ["python", "run.py"]
