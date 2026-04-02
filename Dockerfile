FROM python:3.12-slim

RUN useradd -m -u 1000 appuser
WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.2

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

COPY --chown=appuser:appuser . .

USER appuser
EXPOSE 9180

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9180/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9180"]
