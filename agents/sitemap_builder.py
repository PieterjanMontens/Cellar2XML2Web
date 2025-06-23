import json, yaml, lxml.etree as ET
from datetime import date
from pathlib import Path
from agents.common.kafka_utils import (
    create_avro_consumer,
    create_avro_producer,
    heartbeat, _logger
)

CONFIG = yaml.safe_load(Path("/app/config/base_config.yaml").read_text())
TOPICS = CONFIG["topics"]
SHARED_DIR = Path("/runs")

log = _logger("sitemap_builder", log_topic=TOPICS["logs_app"])
log.info("Starting sitemap builder")

XSLT = ET.XSLT(ET.parse(CONFIG["xslt"]["raw_to_sitemap"]))

# ---------- Avro schemas ----------
IN_SCHEMA = '''
{
  "type":"record",
  "name":"SparqlRaw",
  "fields":[
    {"name":"run_id","type":"string"},
    {"name":"xml",   "type":"string"},
    {"name":"action","type":"string"},
    {"name":"date",  "type":"string"}
  ]
}
'''

OUT_SCHEMA = '''
{
  "type":"record",
  "name":"SitemapRaw",
  "fields":[
    {"name":"run_id","type":"string"},
    {"name":"sitemap","type":"string"},
    {"name":"action", "type":"string"},
    {"name":"date",   "type":"string"}
  ]
}
'''

PRODUCER, _     = create_avro_producer(OUT_SCHEMA)
CONSUMER        = create_avro_consumer("sitemap_builder",
                                       [TOPICS["raw_sparql_out"]],
                                       IN_SCHEMA)

while True:
    try:
        msg = CONSUMER.poll(1.0)
        if msg is None:
            heartbeat(PRODUCER, TOPICS["hb_sitemap_builder"], "sitemap_builder")
            continue
        if msg.error():
            log.error(msg.error())
            continue

        payload = msg.value()
        log.info("Message received, Run id is %s", payload['run_id'])

        xml_in = ET.fromstring(payload["xml"].encode())

        sitemap_xml = XSLT(
                xml_in,
                issuedDate=ET.XSLT.strparam(payload['date']),
                lastmodDate=ET.XSLT.strparam(date.today().isoformat())
                )
        sitemap_txt = str(sitemap_xml)

        ns_out = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        url_count = len(sitemap_xml.xpath('//sm:url', namespaces=ns_out))

        log.info('Sitemap generated, contains %s urls', url_count)

        # dump for debugging
        run_dir = SHARED_DIR / payload["run_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "sitemap.xml").write_text(sitemap_txt)

        PRODUCER.produce(
            TOPICS["raw_sitemap_out"],
            value={**payload, "sitemap": sitemap_txt}
        )
        PRODUCER.flush()
    except Exception as e:
        print("Catched exception ", e)
        log.exception(e)
