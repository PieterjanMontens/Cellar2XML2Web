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
import filecmp
from pathlib import Path
from threading import Thread
from agents.common.kafka_utils import (
    create_avro_consumer,
    create_avro_producer,
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
    {"name":"target","type":"string","default":"prod"}
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
OUT_SCHEMA = '''
{
    "type":"record",
    "name":"Null",
    "fields":[]
}
'''



PRODUCER, _  = create_avro_producer(OUT_SCHEMA)
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
    src = STAGING_DIR / run_id
    if not src.exists():
        raise FileNotFoundError(f"staging site for run {run_id} not found ({src})")

    PROD_DIR.mkdir(parents=True, exist_ok=True)
    _sync_dirs(src, PROD_DIR)

    log.info("Promoted %s → prod", run_id)

def clean(run_id: str):
    target = STAGING_DIR / run_id
    if target.exists():
        shutil.rmtree(target)
        log.info("Deleted staging run %s", run_id)


def _sync_dirs(src: Path, dst: Path):
    """
    Copy newer/changed files from src → dst. Remove files in dst that are
    no longer present in src. Sub-dirs created as needed.
    """
    # 1. Copy & overwrite newer files
    shutil.copytree(src, dst, dirs_exist_ok=True)

    # 2. Remove stale files
    # Walk dst; if relative path not in src, delete it.
    for root, dirs, files in os.walk(dst, topdown=False):
        rel_root = Path(root).relative_to(dst)
        src_root = src / rel_root

        # Files
        for f in files:
            if not (src_root / f).exists():
                os.remove(Path(root) / f)
        # Dirs
        for d in dirs:
            dst_dir = Path(root) / d
            if not (src_root / d).exists():
                shutil.rmtree(dst_dir)

# ─── Start HTTP server in background ─────────────────────────────────────────
Thread(target=start_http, daemon=True).start()

# ─── Main loop: process Kafka commands ───────────────────────────────────────
while True:
    try:
            msg = CONSUMER.poll(1.0)
            if msg is None:
                heartbeat(PRODUCER, TOPICS["hb_web_builder"], "web_builder")
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
        break
    except Exception as e:
        print("Catched exception ", e)
        log.exception(e)
