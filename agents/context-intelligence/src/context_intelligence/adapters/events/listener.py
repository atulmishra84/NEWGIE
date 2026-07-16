"""Kafka listener entrypoint."""

from __future__ import annotations

from context_intelligence.infrastructure.messaging.kafka_consumer import run_consumer


def main() -> None:
    run_consumer()


if __name__ == "__main__":
    main()
