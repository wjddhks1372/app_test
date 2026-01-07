FROM python:3.9-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# 이 줄이 정확히 있어야 합니다!
CMD ["python", "app.py"]