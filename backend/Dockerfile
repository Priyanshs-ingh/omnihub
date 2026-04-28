FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy only the project metadata first to maximize layer cache reuse.
COPY pyproject.toml README.md ./

# Pre-install dependencies. ".[dev]" is intentionally omitted in prod images.
RUN pip install --upgrade pip && pip install .

# Now bring in the app source and data.
COPY app ./app

# Render/Railway/Fly inject PORT; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

# 2 workers is fine for the demo load; bump for production.
CMD ["sh", "-c", "gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT}"]
