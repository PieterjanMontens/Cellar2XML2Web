FROM python:3.11-slim
WORKDIR /app
COPY config ./config
RUN pip install --no-cache-dir requests lxml pyyaml Jinja2 confluent-kafka[avro,schemaregistry] python-ulid

# ---------- Node / Eleventy layer ----------
RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y nodejs \
 && npm install -g @11ty/eleventy@^3.0.0 \
 && npm install fast-xml-parser -g \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH /app
CMD ["python"]
