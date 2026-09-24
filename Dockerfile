FROM node:22-bookworm-slim AS frontend

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY vite.config.js tailwind.config.js postcss.config.js ./
COPY frontend/ ./frontend/
COPY templates/ ./templates/
RUN npm run build

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /build/static/dist/ /app/static/dist/
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin antidote \
    && mkdir -p /app/data /app/media /app/staticfiles \
    && chown -R antidote:antidote /app/data /app/media /app/staticfiles \
    && chmod +x /app/deploy/docker-entrypoint.sh

USER antidote
EXPOSE 8000

ENTRYPOINT ["/app/deploy/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--worker-class", "gthread", "--access-logfile", "-", "--error-logfile", "-", "config.wsgi:application"]
