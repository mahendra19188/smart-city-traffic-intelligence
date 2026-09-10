import json
import time

from kafka import KafkaProducer

from src.ingestion.traffic_generator import generate_traffic_event


KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "traffic-events"


def create_producer():
    return KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda value: json.dumps(value).encode("utf-8")
    )


def main():

    producer = create_producer()

    print("Smart City Traffic Kafka Producer")
    print("---------------------------------")
    print(f"Kafka Broker : {KAFKA_BROKER}")
    print(f"Kafka Topic  : {KAFKA_TOPIC}")
    print()

    try:

        while True:

            event = generate_traffic_event()

            producer.send(
                KAFKA_TOPIC,
                value=event
            )

            producer.flush()

            print(
                f"Sent | "
                f"{event['event_id']} | "
                f"{event['road_name']} | "
                f"Vehicles: {event['vehicle_count']} | "
                f"Speed: {event['average_speed_kmh']} km/h | "
                f"Incident: {event['incident_flag']}"
            )

            time.sleep(2)

    except KeyboardInterrupt:

        print("\nStopping Kafka producer...")

    finally:

        producer.close()


if __name__ == "__main__":
    main()