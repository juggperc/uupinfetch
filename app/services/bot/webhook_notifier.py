"""
Webhook notification service for Discord, Telegram, and generic HTTP endpoints.
Replaces the inline webhook logic from the monolithic bot_engine.
"""

import asyncio
import logging
import ipaddress
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy.orm import Session
from app.models.models import WebhookConfig

logger = logging.getLogger(__name__)

class WebhookNotifier:
    """Send notifications to configured webhooks."""
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Prevent SSRF: reject private IP ranges and non-http(s) schemes."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = parsed.hostname
            if not hostname:
                return False
            # Check for private IPs
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_reserved:
                    return False
            except ValueError:
                # It's a domain name — allow it
                pass
            # Reject localhost by name
            if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
                return False
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_webhooks(db: Session, active_only: bool = True) -> List[Dict[str, Any]]:
        query = db.query(WebhookConfig)
        if active_only:
            query = query.filter(WebhookConfig.active == True)
        rows = query.order_by(WebhookConfig.created_at.desc()).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "webhook_type": r.webhook_type,
                "url": r.url,
                "events": r.events,
                "active": r.active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    
    @staticmethod
    def add_webhook(db: Session, name: str, webhook_type: str, url: str, events: str) -> int:
        if not WebhookNotifier.validate_url(url):
            raise ValueError("Invalid or unsafe webhook URL")
        wh = WebhookConfig(name=name, webhook_type=webhook_type, url=url, events=events)
        db.add(wh)
        db.commit()
        db.refresh(wh)
        return wh.id
    
    @staticmethod
    def remove_webhook(db: Session, webhook_id: int) -> bool:
        wh = db.query(WebhookConfig).filter(WebhookConfig.id == webhook_id).first()
        if not wh:
            return False
        db.delete(wh)
        db.commit()
        return True
    
    @staticmethod
    async def _send_single(webhook: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        url = webhook.get("url", "")
        wh_type = webhook.get("webhook_type", "generic")
        if not url:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                if wh_type == "discord":
                    content = payload.get("message", "")
                    await client.post(url, json={"content": content})
                elif wh_type == "telegram":
                    text = payload.get("message", "")
                    if "/bot" in url and "sendMessage" not in url:
                        tg_url = f"{url}/sendMessage" if not url.endswith("/") else f"{url}sendMessage"
                    else:
                        tg_url = url
                    await client.post(tg_url, json={"text": text, "parse_mode": "HTML"})
                else:
                    await client.post(url, json=payload)
            return True
        except Exception as e:
            logger.warning(f"Webhook delivery failed for {wh_type}: {e}")
            return False
    
    @staticmethod
    async def notify(db: Session, event_type: str, data: Dict[str, Any]):
        """Notify all webhooks subscribed to a given event type."""
        webhooks = WebhookNotifier.get_webhooks(db, active_only=True)
        if not webhooks:
            return
        
        for wh in webhooks:
            events = wh.get("events", "")
            if event_type not in events:
                continue
            
            payload = {"event": event_type, "message": data.get("message", ""), "data": data}
            asyncio.create_task(WebhookNotifier._send_single(wh, payload))
