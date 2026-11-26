
FROM python:3.11.9-slim-bookworm@sha256:8fb099199b9f2d70342674bd9dbccd3ed03a258f26bbd1d556822c6dfc60c317

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-serving.txt .

RUN python -m pip install --no-cache-dir --timeout 120 --retries 5 -r requirements-serving.txt \
    && python -m pip check

COPY app/ ./app/
COPY models/churn_model.joblib ./models/churn_model.joblib

RUN groupadd --system app && useradd --system --gid app --no-create-home app
USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/ready', timeout=2).close()"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
