from __future__ import annotations
from gie_contracts.integration import AuditLogEntry, PlatformId, WebhookEvent, WebhookIngressRequest
from gie_contracts.integration_events import WebhookReceived
from gie_observability.logging import get_logger
from integration_intelligence.domain.engine import ingest_webhook
from integration_intelligence.domain.ports import AuditRepository, EventPublisher, WebhookRepository
from integration_intelligence.settings import Settings
from integration_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)

class WebhookHandler:
    def __init__(self, *, webhooks: WebhookRepository, audits: AuditRepository, events: EventPublisher, settings: Settings):
        self._webhooks = webhooks
        self._audits = audits
        self._events = events
        self._settings = settings

    async def handle(
        self,
        platform_id: PlatformId,
        body: WebhookIngressRequest,
        *,
        raw_body: bytes,
        actor: str,
        correlation_id: str,
        tenant_fallback: str,
    ) -> WebhookEvent:
        event = ingest_webhook(
            platform_id,
            body,
            raw_body=raw_body,
            hmac_secret=self._settings.webhook_hmac_secret,
            tenant_fallback=tenant_fallback,
        )
        await self._webhooks.save(event)
        await self._audits.save(
            AuditLogEntry(
                tenant_id=event.tenant_id,
                actor=actor,
                action="integration.webhook",
                resource_type="webhook",
                resource_id=str(event.event_id),
                platform_id=platform_id,
                outcome=event.delivery_status.value,
                detail={"event_type": event.event_type, "signature_valid": event.signature_valid},
            )
        )
        evt = WebhookReceived(
            tenant_id=event.tenant_id,
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            event_id_ref=event.event_id,
            platform_id=platform_id.value,
            event_type_name=event.event_type,
        )
        await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=str(event.event_id))
        logger.info("webhook_received", platform=platform_id.value, status=event.delivery_status.value)
        return event
