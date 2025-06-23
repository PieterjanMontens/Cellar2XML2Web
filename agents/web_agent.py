"""
Web-Agent
─────────
* Serves both **staging** and **production** HTML trees over HTTP.
* Listens to two *Avro* command topics:
    • `cmd.web_agent.deploy`  – promote a run_id from /srv/staging → /srv/prod
    • `cmd.web_agent.clean`   – delete a run_id from /srv/staging
* Emits heart-beats (`hb_web_agent`) and structured logs (`logs_app`).

Directory layout (defined in base_config.yaml):
    /srv/staging/<run_id>/_site/…   ← written by Web-Builder
    /srv/prod/                      ← active public site
"""

import os, json, time, shutil, http.server, socketserver, yaml, signal
from pathlib import Path
from threading import Thread
from agents.common.kafka_utils import (
    create_avro_consumer,
    heartbeat,
    _logger
)

# ─── Configuration ────────────────────────────────────────────────────────────
CONFIG       = yaml.safe_load(Path("/app/config/base_config.yaml").read_text())
TOPICS       = CONFIG["topics"]
WEB_CFG      = CONFIG.get("web_agent", {})          # optional future fields

STAGING_DIR  = Path("/srv/staging")
PROD_DIR     = Path("/srv/prod")
PORT         = int(os.getenv("WEB_AGENT_PORT", 8080))

log = _logger("web_agent", log_topic=TOPICS["logs_app"])
log.info("Starting web agent")

# ─── Avro schemas for command topics ──────────────────────────────────────────
DEPLOY_SCHEMA = """
{
  "type":"record",
  "name":"DeployCmd",
  "fields":[
    {"name":"run_id","type":"string"},
    {"name":"target","type":{"type":"enum","name":"Stage","symbols":["prod","staging"]},"default":"prod"}
  ]
}
"""
CLEAN_SCHEMA = """
{
  "type":"record",
  "name":"CleanCmd",
  "fields":[{"name":"run_id","type":"string"}]
}
"""

CONSUMER = create_avro_consumer(
    group="web_agent_cmds",
    topics=[TOPICS["cmd_web_agent_deploy"], TOPICS["cmd_web_agent_clean"]],
    value_schema_str=DEPLOY_SCHEMA  # will also work for CLEAN (extra field ignored)
)

# ─── HTTP Server: / → prod , /staging/<run_id>/ → staging ─────────────────────
class RouterHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, url: str) -> str:
        if url.startswith("/staging/"):
            return str(Path("/srv") / url.lstrip("/"))
        return str(PROD_DIR / url.lstrip("/"))

def start_http():
    with socketserver.TCPServer(("", PORT), RouterHandler) as httpd:
        log.info("Serving staging=%s and prod=%s on :%s", STAGING_DIR, PROD_DIR, PORT)
        httpd.serve_forever()

# ─── Helper actions ───────────────────────────────────────────────────────────
def promote(run_id: str):
    src = STAGING_DIR / run_id / "_site"
    if not src.exists():
        raise FileNotFoundError(f"staging site for run {run_id} not found ({src})")
    # Atomically replace prod by copy-tree + rename
    tmp = PROD_DIR.with_suffix(".tmp")
    if tmp.exists(): shutil.rmtree(tmp)
    shutil.copytree(src, tmp, dirs_exist_ok=True)
    if PROD_DIR.exists(): shutil.rmtree(PROD_DIR)
    tmp.rename(PROD_DIR)
    log.info("Promoted %s → prod", run_id)

def clean(run_id: str):
    target = STAGING_DIR / run_id
    if target.exists():
        shutil.rmtree(target)
        log.info("Deleted staging run %s", run_id)

# ─── Start HTTP server in background ─────────────────────────────────────────
Thread(target=start_http, daemon=True).start()

# ─── Main loop: process Kafka commands ───────────────────────────────────────
try:
    while True:
        msg = CONSUMER.poll(1.0)
        if msg is None:
            heartbeat(TOPICS["hb_web_agent"], "web_agent")
            continue
        if msg.error():
            log.error(msg.error())
            continue

        topic = msg.topic()
        cmd   = msg.value()     # Avro → dict
        try:
            if topic == TOPICS["cmd_web_agent_deploy"]:
                promote(cmd["run_id"])
            elif topic == TOPICS["cmd_web_agent_clean"]:
                clean(cmd["run_id"])
            else:
                log.warning("Unknown command topic %s", topic)
        except Exception as exc:
            log.error("Command failed: %s", exc)

except KeyboardInterrupt:
    log.info("Shutting down Web-Agent.")
except Exception as e:
    print("Catched exception ", e)
    log.exception(e)
