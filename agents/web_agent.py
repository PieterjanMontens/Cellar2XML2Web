import http.server, os, socketserver
from pathlib import Path
import yaml
from agents.common.kafka_utils import create_consumer, create_producer, heartbeat, _logger

log = _logger("web_agent")

CONFIG = yaml.safe_load(Path("/app/config/base_config.yaml").read_text())
TOPICS = CONFIG["topics"]
CONSUMER = create_consumer("web_agent", [])
PRODUCER = create_producer()

WEBROOT = Path("/app/output")
PORT = 8080

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEBROOT), **kwargs)

def serve_forever():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        log.info("Serving %s on %s", WEBROOT, PORT)
        httpd.serve_forever()

if os.fork() == 0:
    serve_forever()

while True:
    heartbeat(PRODUCER, TOPICS["hb_web_agent"], "web_agent")
