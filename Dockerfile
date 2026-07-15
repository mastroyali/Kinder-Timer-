FROM python:3.10-slim

# Создаем рабочую директорию
WORKDIR /code

# Устанавливаем зависимости
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Копируем весь проект в контейнер
COPY . .

# Hugging Face Spaces по умолчанию ожидает, что приложение будет слушать порт 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
