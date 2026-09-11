FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt requirements.txt
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api/requirements.txt
COPY mapper/ mapper/
COPY api/ api/
COPY polymarket/ polymarket/
COPY protoc_gen_openapiv2/ protoc_gen_openapiv2/
COPY --from=web /web/dist web/dist
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "180", "api.app:app"]
