import os, json, time, uuid, logging, sys
from confluent_kafka import Producer, SerializingProducer, DeserializingConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
SCHEMA_REGISTRY   = os.getenv("SCHEMA_REGISTRY", "http://schema-registry:8081")

def _logger(name: str, log_topic: str | None = None) -> logging.Logger:
    """Returns a logger; if *log_topic* is set, adds a Kafka handler."""
    logger = logging.getLogger(name)
    if logger.handlers:               # already initialised → return as is
        return logger

    logger.setLevel(logging.DEBUG)

    # Console/stdout
    stream = logging.StreamHandler()
    stream.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
    )
    logger.addHandler(stream)

    # Kafka
    if log_topic:
        logger.addHandler(_KafkaLogHandler(log_topic, component=name))

    return logger

_sr_client = SchemaRegistryClient({"url": SCHEMA_REGISTRY})
_plain_producer = Producer({"bootstrap.servers": BOOTSTRAP_SERVERS})

def _dict_to_bytes(obj, ctx):
    # Serializer helper—not used, value schema only
    return obj

def create_avro_producer(value_schema_str: str):
    """
    Returns (producer, value_serializer) so callers can:
        producer.produce(topic, key=None,
                         value=value_serializer(payload, ctx))
    """
    value_serializer = AvroSerializer(
        _sr_client,
        value_schema_str,
        _dict_to_bytes
    )

    producer = SerializingProducer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "enable.idempotence": True,
        "linger.ms": 0,
        "batch.size": 16384,
        "delivery.timeout.ms": 30000,
        "value.serializer": value_serializer,
    })
    return producer, value_serializer

def create_avro_consumer(group, topics, value_schema_str: str):
    value_deserializer = AvroDeserializer(_sr_client, value_schema_str)

    consumer = DeserializingConsumer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": group,
        "auto.offset.reset": "earliest",
        "value.deserializer": value_deserializer,
    })
    consumer.subscribe(topics)
    return consumer

def heartbeat(producer, topic, component):
    _plain_producer.produce(
        topic,
        json.dumps({"ts": time.time(), "component": component}).encode()
    )
    _plain_producer.poll(0)

# kafka-backed log handler
class _KafkaLogHandler(logging.Handler):
    def __init__(self, topic: str, component: str):
        super().__init__(level=logging.INFO)     # forward INFO and up
        self.topic      = topic
        self.component  = component

    def emit(self, record):
        if record.levelno < logging.INFO:
            return
        payload = {
            "ts":       record.created,
            "component": self.component,
            "level":    record.levelname,
            "msg":      record.getMessage()
        }
        try:
            _plain_producer.produce(
                self.topic,
                json.dumps(payload).encode()
            )
            _plain_producer.poll(0)
        except Exception as exc:
            print("KafkaLogHandler error:", exc, file=sys.stderr)

