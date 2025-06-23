FROM python:3.11-slim
WORKDIR /app
COPY config ./config
RUN pip install --no-cache-dir requests lxml pyyaml Jinja2 confluent-kafka[avro,schemaregistry] python-ulid

# --- Node + Eleventy ---
RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y nodejs \
 && npm install -g @11ty/eleventy@^3.0.0

# --- Node dependencies outside bind-mount ---
COPY templates/package*.json /deps/
RUN npm ci --production --prefix /deps \
 && mv /deps/node_modules /opt/node_modules \
 && rm -rf /deps
ENV NODE_PATH=/opt/node_modules

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
CMD ["python"]
