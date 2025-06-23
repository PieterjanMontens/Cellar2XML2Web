import json, yaml, time, requests, os
from pathlib import Path
from agents.common.kafka_utils import (
    create_avro_producer,
    create_avro_consumer,
    heartbeat, _logger
)
from agents.common.id_utils import new_run_id
from pathlib import Path

CONFIG = yaml.safe_load(Path("/app/config/base_config.yaml").read_text())
TOPICS = CONFIG["topics"]
SHARED_DIR = Path("/runs")

log = _logger("query_agent", log_topic=TOPICS["logs_app"])
log.info("Starting query agent")


# --- Avro schema definitions ---
CMD_SCHEMA = '''
{
  "type":"record",
  "name":"Cmd",
  "fields":[{"name":"date","type":"string"},{"name":"collection","type":"string"}]
}
'''

OUT_SCHEMA = '''
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

PRODUCER, to_avro = create_avro_producer(OUT_SCHEMA)
CONSUMER          = create_avro_consumer("query_agent_cmd",
                                         [TOPICS["cmd_query_agent"]],
                                         CMD_SCHEMA)


def run_query(sparql, endpoint, date_param):

    headers = {
        "Accept": "application/sparql-results+xml, application/xml;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    r = requests.post(
            endpoint,
            data={"query": sparql.replace("<date>", date_param),
                  "default-graph-uri": "",
                  "format": "application/sparql-results+xml",
                  "timeout":0},
            headers=headers
    )
    r.raise_for_status()
    return r.text

while True:
    try:
        msg = CONSUMER.poll(1.0)
        if msg is None:
            heartbeat(PRODUCER, TOPICS["hb_query_agent"], "query_agent")
            continue
        if msg.error():
            log.error(msg.error())
            continue

        log.debug(f"Message received {msg.timestamp()}: {msg.topic()}, Partition: {msg.partition()}, Offset: {msg.offset()}")
        log.debug("Message contents:", msg.value())
        payload = msg.value()
        date_param = payload["date"]
        collection_param = payload["collection"]
        action =  collection_param
        run_id = new_run_id(date_param)
        run_dir = SHARED_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        log.info("Message received, Run id is %s", run_id)

        if action not in CONFIG["sparql_queries"]:
            log.warning(f"Could not find {action} in available sparql query definitions")
            continue

        cfg = CONFIG["sparql_queries"][action]
        if 'date' in cfg['parameter']:
            query = cfg["query"].replace('<date>', date_param)
        else:
            query = cfg["query"]

        (run_dir / "sparql_query.rdf").write_text(query)


        log.debug('Raw Sparql query:', query)
        log.info("Running SPARQL for %s on %s", action, date_param)

        xml = run_query(cfg["query"], cfg["endpoint"], date_param)

        log.info("Results obtained,  %s characters", len(xml))

        (run_dir / "sparql_results.xml").write_text(xml)

        k_payload={
            "run_id": run_id,
            "xml": xml,
            "action": action,
            "date": date_param
        }

        PRODUCER.produce(TOPICS["raw_sparql_out"],
                         value=k_payload)

        PRODUCER.flush()
    except KeyboardInterrupt:
        log.info("Shutting down query agent.")
        break
    except Exception as e:
        print("Catched exception ", e)
        log.exception(e)
