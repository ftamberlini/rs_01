FROM python:3.12-slim

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml .
RUN uv pip install --system --no-cache "fastapi[standard]>=0.115" "python-multipart>=0.0.9"

COPY index.html .
COPY main.py .
COPY css/ css/
COPY js/ js/
COPY data/ data/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
