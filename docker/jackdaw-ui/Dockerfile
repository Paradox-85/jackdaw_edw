FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt is at docker/jackdaw-ui/requirements.txt in build context (edw/ root)
COPY docker/jackdaw-ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ui/ is the Python package; ui/app.py is the Streamlit entrypoint
COPY ui/ ./ui/

# Streamlit config (theme, server settings)
COPY .streamlit/ ./.streamlit/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "ui/app.py", "--server.address=0.0.0.0"]
