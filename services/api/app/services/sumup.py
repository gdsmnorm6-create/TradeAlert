from dataclasses import dataclass

import httpx

from app.config import Settings
from app.models import Invoice


@dataclass
class CheckoutResult:
    checkout_id: str
    checkout_url: str


async def create_hosted_checkout(invoice: Invoice, settings: Settings) -> CheckoutResult:
    if not settings.sumup_api_key or not settings.sumup_merchant_code:
        return CheckoutResult(
            checkout_id=f"demo-{invoice.id}",
            checkout_url=f"https://checkout.sumup.com/pay/demo-{invoice.id}",
        )

    amount = invoice.amount_minor / 100
    payload = {
        "checkout_reference": invoice.id,
        "amount": amount,
        "currency": invoice.currency,
        "merchant_code": settings.sumup_merchant_code,
        "description": f"TradeAlert invoice {invoice.number}",
        "hosted_checkout": {"enabled": True},
        "redirect_url": f"{settings.mobile_deep_link_base}invoices/{invoice.id}",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.sumup.com/v0.1/checkouts",
            headers={"Authorization": f"Bearer {settings.sumup_api_key}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    return CheckoutResult(checkout_id=data["id"], checkout_url=data["hosted_checkout_url"])

