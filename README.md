# Cellar2XML2Web PoC

## Quick start

```bash
# Start everything:
docker compose up -d

# Restart after config change
docker compose restart
docker compose restart [agent]
```

1. Browse to `http://localhost:3000` – pick a date and press **Run**  
2. Follow logs with `docker compose logs -f`  
3. Generated site becomes available at `http://localhost:8080/<date>/`
4. Zookeeper can be monitored at `http://localhost:9000/` (connection string: `zookeeper:2181`)


**Happy hacking!**

## Notes
- Schemas are managed and versioned automatically by the registry: any serious usage should 
instead use pre-registered schemas
- Used a Kafka+Zookeeper approach. This doesn't use the latest KRaft feature, and is not aligned with Kafka 4.0+

## Kafka topics & agents

| Agent / UI | Tech | Consumes | Produces | Purpose |
|------------|------|----------|----------|---------|
| **Control Panel** | HTML + JS (browser) | – | `cmd.query_agent` | Sends manual *date* commands to start a run. |
| **Query Agent** | Python | `cmd.query_agent` | `raw.sparql.out`<br>`hb_query_agent`<br>`logs_app` | Runs the SPARQL query for the requested date, pushes the raw XML result, emits heart-beats and structured logs. |
| **Sitemap Builder** | Python + XSLT 3 | `raw.sparql.out` | `raw.sitemap.out`<br>`hb_sitemap_builder`<br>`logs_app` | Transforms raw XML into a sitemap XML using streaming XSLT. |
| **Web Builder** | Python + Eleventy | `raw.sitemap.out` | *(files on disk)*<br>`hb_web_builder`<br>`logs_app` | Converts sitemap → static HTML site, grouped by Date → OJ-collection → resource-type → agents. |
| **Web Agent** | Python (simple HTTP) | – | `hb_web_agent`<br>`logs_app` | Serves the generated site and syncs staging ↔ prod on request. |
| **Web Portal** | Nginx (static) | – | – | Public-facing endpoint (read-only). |
| **Schema Registry** | CP image | – | – | Stores Avro schemas for `cmd.*`, `raw.*` topics. |
| **Kafka Broker** | CP image | – | – | Backbone message bus (auto-creates topics on first write). |
| **ZooKeeper** (or KRaft) | CP image | – | – | Coordination layer for single-broker demo. |

### Cross-cutting topics

| Topic | Producer(s) | Consumer(s) | Format | Purpose |
|-------|-------------|-------------|--------|---------|
| `cmd.query_agent` | Control Panel (REST Proxy) | Query Agent | Avro | Human commands: `{ "date": "YYYY-MM-DD" }` |
| `raw.sparql.out`  | Query Agent | Sitemap Builder | Avro | Raw SPARQL XML payloads. |
| `raw.sitemap.out` | Sitemap Builder | Web Builder | Avro | Sitemap XML + metadata. |
| `logs_app`        | All Python agents (INFO+) | Control Panel (JS) | JSON | Centralised structured logs (streamed into the UI). |
| `hb_*` (one per agent) | Each agent (every 5 s) | Grafana/alerts | JSON | Liveness heart-beats: `{ ts, component }`. |
| `config.updates`* | Control Panel (future) | All agents | JSON | Hot-reload shared YAML without restarts. |
| `*.DLQ`* | Any agent | Ops tooling | JSON | Dead-letter queues for failed deserialisation / validation. |

\* *Optional topics not yet wired in the skeleton.*
