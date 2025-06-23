import json, os, yaml, subprocess
from pathlib import Path
import shutil, tarfile
from agents.common.kafka_utils import (
    create_avro_consumer,
    create_avro_producer,
    heartbeat, _logger
)

CONFIG = yaml.safe_load(Path("/app/config/base_config.yaml").read_text())
TOPICS = CONFIG["topics"]
WEBCFG  = CONFIG["web"]
SHARED_DIR = Path("/runs")
TEMPLATES = CONFIG["web"]["eleventy_template_dir"]
OUTPUT_DIR = Path(CONFIG["web"]["output_dir"])

log = _logger("web_builder", log_topic=TOPICS["logs_app"])
log.info("Starting web builder")

# ---------- INIT ----------
log.debug('Trying to ensure fast-xml-parser availability') 
subprocess.check_call(["npm", "install", "--no-save", "fast-xml-parser@^5"], cwd="/app/templates")

# ---------- Avro in-schema ----------
IN_SCHEMA = '''
{
  "type":"record",
  "name":"SitemapRaw",
  "fields":[
    {"name":"run_id",  "type":"string"},
    {"name":"sitemap", "type":"string"},
    {"name":"action",  "type":"string"},
    {"name":"date",    "type":"string"}
  ]
}
'''
OUT_SCHEMA = '''
{
    "type":"record",
    "name":"Null",
    "fields":[]
}
'''

# We only *consume* Avro records
PRODUCER, _  = create_avro_producer(OUT_SCHEMA)
CONSUMER = create_avro_consumer("web_builder",
                                [TOPICS["raw_sitemap_out"]],
                                IN_SCHEMA)
def build_site():
    subprocess.check_call(["npx", "@11ty/eleventy", "--input", TEMPLATES, "--output", OUTPUT_DIR])

while True:
    try:
        msg = CONSUMER.poll(1.0)
        if msg is None:
            heartbeat(PRODUCER, TOPICS["hb_web_builder"], "web_builder")
            continue
        if msg.error():
            log.error(msg.error())
            continue

        payload = msg.value()
        log.info("Message received, Run id is %s", payload['run_id'])

        # 1)  write Eleventy input files *inside* the site
        site_dir = OUTPUT_DIR / payload["run_id"]
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "sitemap.xml").write_text(payload["sitemap"])
        (site_dir / "metadata.json").write_text(json.dumps(payload, indent=2))

        log.info("Generating static HTML files...")
        # 2)  call Eleventy, output to OUTPUT_DIR/<run_id>/
        env = os.environ.copy()
        env["RUN_DIR"] = str(site_dir)
        subprocess.check_call([
            "eleventy",
            "--input", "/app/templates",
            "--output", str(site_dir)
        ], cwd="/app/templates", env=env)        # Eleventy’s CWD → run-dir (has sitemap.xml)

        log.info("Static HTML files generated, packaging...")
        # 3a)  tar-gz the rendered site for inspection
        run_dir = SHARED_DIR / payload["run_id"]
        run_dir.mkdir(parents=True, exist_ok=True)

        tar_path = run_dir / "site.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(site_dir, arcname="site")

        # 3b)  uncompressed copy for quick inspection  (optional)
        if WEBCFG.get("debug_copy_to_runs", False):
            debug_dir = run_dir / "build"
            if debug_dir.exists():
                shutil.rmtree(debug_dir)
            shutil.copytree(site_dir, debug_dir)

        log.info("Site built and staged → %s (and archived at %s)", site_dir, tar_path)

    except KeyboardInterrupt:
        log.info("Shutting down web builder.")
        break
    except Exception as e:
        print("Catched exception ", e)
        log.exception(e)
