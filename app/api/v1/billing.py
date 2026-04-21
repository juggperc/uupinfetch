from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
import logging
from app.db.database import get_db
from app.models.models import User
from app.core.config import get_settings
from app.core.auth import require_auth

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

# Initialize Polar client lazily
def get_polar_client():
    try:
        from polar import Polar
        return Polar(
            access_token=settings.POLAR_ACCESS_TOKEN,
            server=settings.POLAR_SERVER,
        )
    except Exception as e:
        logger.error(f"Failed to initialize Polar client: {e}")
        return None

@router.post("/checkout/pro")
async def create_pro_checkout(user: User = Depends(require_auth)):
    """Create a Polar checkout session for Pro plan."""
    client = get_polar_client()
    if not client:
        raise HTTPException(status_code=503, detail="Billing service unavailable")
    if not settings.POLAR_PRO_PRODUCT_ID:
        raise HTTPException(status_code=503, detail="Pro product not configured")
    
    try:
        checkout = client.checkouts.custom.create(
            product_price_id=settings.POLAR_PRO_PRODUCT_ID,
            customer_email=user.email,
            customer_name=user.name or user.email.split("@")[0],
            metadata={"user_id": str(user.id)},
            success_url=settings.POLAR_SUCCESS_URL,
        )
        return {"checkout_url": checkout.url}
    except Exception as e:
        logger.error(f"Polar checkout error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout")

@router.post("/checkout/enterprise")
async def create_enterprise_checkout(user: User = Depends(require_auth)):
    """Create a Polar checkout session for Enterprise plan."""
    client = get_polar_client()
    if not client:
        raise HTTPException(status_code=503, detail="Billing service unavailable")
    if not settings.POLAR_ENTERPRISE_PRODUCT_ID:
        raise HTTPException(status_code=503, detail="Enterprise product not configured")
    
    try:
        checkout = client.checkouts.custom.create(
            product_price_id=settings.POLAR_ENTERPRISE_PRODUCT_ID,
            customer_email=user.email,
            customer_name=user.name or user.email.split("@")[0],
            metadata={"user_id": str(user.id)},
            success_url=settings.POLAR_SUCCESS_URL,
        )
        return {"checkout_url": checkout.url}
    except Exception as e:
        logger.error(f"Polar checkout error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout")

@router.get("/subscription")
async def get_subscription(user: User = Depends(require_auth)):
    """Get current user's subscription status."""
    client = get_polar_client()
    subscriptions = []
    
    if client and user.polar_customer_id:
        try:
            subs = client.subscriptions.list(
                customer_id=user.polar_customer_id,
                active=True,
            )
            subscriptions = [sub.to_dict() for sub in subs.items] if hasattr(subs, 'items') else []
        except Exception as e:
            logger.error(f"Failed to fetch subscriptions: {e}")
    
    return {
        "plan": user.subscription_plan,
        "status": user.subscription_status,
        "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
        "polar_subscriptions": subscriptions,
    }

@router.post("/portal")
async def create_customer_portal(user: User = Depends(require_auth)):
    """Create a customer portal session for managing billing."""
    client = get_polar_client()
    if not client or not user.polar_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription found")
    
    try:
        # Polar Customer Portal API
        session = client.customer_sessions.create(
            customer_id=user.polar_customer_id,
        )
        return {"portal_url": session.customer_portal_url}
    except Exception as e:
        logger.error(f"Failed to create customer portal: {e}")
        raise HTTPException(status_code=500, detail="Failed to create customer portal")

@router.post("/webhook")
async def polar_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Polar webhook events for subscription lifecycle."""
    body = await request.body()
    
    # Verify webhook signature if secret is configured
    if settings.POLAR_WEBHOOK_SECRET:
        import hmac
        import hashlib
        signature = request.headers.get("x-polar-signature", "")
        expected = hmac.new(
            settings.POLAR_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    
    try:
        payload = await request.json()
        event_type = payload.get("type", "")
        data = payload.get("data", {})
        
        metadata = data.get("metadata", {})
        user_id = metadata.get("user_id")
        customer_id = data.get("customer_id")
        
        if event_type == "subscription.active":
            # Subscription activated
            user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
            if not user and customer_id:
                user = db.query(User).filter(User.polar_customer_id == customer_id).first()
            if user:
                user.polar_customer_id = customer_id
                user.subscription_status = "active"
                product_name = data.get("product", {}).get("name", "").lower()
                if "enterprise" in product_name:
                    user.subscription_plan = "enterprise"
                elif "pro" in product_name:
                    user.subscription_plan = "pro"
                db.commit()
                logger.info(f"Subscription activated for user {user.id}")
        
        elif event_type == "subscription.canceled":
            user = db.query(User).filter(User.polar_customer_id == customer_id).first()
            if user:
                user.subscription_status = "cancelled"
                db.commit()
                logger.info(f"Subscription cancelled for user {user.id}")
        
        elif event_type == "subscription.revoked":
            user = db.query(User).filter(User.polar_customer_id == customer_id).first()
            if user:
                user.subscription_status = "inactive"
                user.subscription_plan = "free"
                db.commit()
                logger.info(f"Subscription revoked for user {user.id}")
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.get("/products")
async def list_products():
    """List available billing products/plans."""
    client = get_polar_client()
    if not client:
        return {"products": []}
    
    try:
        products = client.products.list()
        return {"products": [p.to_dict() for p in products.items] if hasattr(products, 'items') else []}
    except Exception as e:
        logger.error(f"Failed to list products: {e}")
        return {"products": []}
