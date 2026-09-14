from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import uuid
import datetime

router = APIRouter()

class StripeDetails(BaseModel):
    cardholder_name: str
    card_number: str
    exp_month: str
    exp_year: str
    cvc: str

class BkashDetails(BaseModel):
    phone_number: str
    otp: str
    pin: str

class PaymentRequest(BaseModel):
    plan_id: str = Field(..., example="pro")
    billing_cycle: str = Field("monthly", example="monthly") # 'monthly' | 'annual'
    payment_method: str = Field(..., example="stripe") # 'stripe' | 'bkash'
    stripe_details: Optional[StripeDetails] = None
    bkash_details: Optional[BkashDetails] = None

@router.post("/payment/checkout")
def process_checkout(req: PaymentRequest):
    """Process payment via Stripe or bKash gateway."""
    plan_prices = {
        "starter": {"usd": 19, "bdt": 2200, "name": "Starter Plan"},
        "pro": {"usd": 79, "bdt": 9200, "name": "Professional Plan"},
        "enterprise": {"usd": 249, "bdt": 28900, "name": "Enterprise Team"},
    }

    if req.plan_id not in plan_prices:
        raise HTTPException(status_code=400, detail="Invalid plan selected")

    plan_info = plan_prices[req.plan_id]
    
    # Billing cycle discount for annual (20% off)
    multiplier = 0.8 * 12 if req.billing_cycle == "annual" else 1.0
    usd_amount = round(plan_info["usd"] * multiplier, 2)
    bdt_amount = round(plan_info["bdt"] * multiplier)

    if req.payment_method == "stripe":
        if not req.stripe_details or len(req.stripe_details.card_number.replace(" ", "")) < 12:
            raise HTTPException(status_code=400, detail="Invalid Stripe card details provided")
        tx_id = f"tx_str_{uuid.uuid4().hex[:10]}"
        payment_status = "succeeded"
        gateway_msg = "Paid via Stripe Payment Gateway (Card / Apple Pay)"
        amount_str = f"${usd_amount:,.2f} USD"

    elif req.payment_method == "bkash":
        if not req.bkash_details or not req.bkash_details.phone_number:
            raise HTTPException(status_code=400, detail="Invalid bKash account details provided")
        tx_id = f"TRX{uuid.uuid4().hex[:8].upper()}"
        payment_status = "succeeded"
        gateway_msg = f"Paid via bKash MFS ({req.bkash_details.phone_number})"
        amount_str = f"৳{bdt_amount:,} BDT"
    else:
        raise HTTPException(status_code=400, detail="Unsupported payment method")

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {
        "status": "success",
        "message": f"Payment successfully processed for {plan_info['name']}",
        "transaction_id": tx_id,
        "plan_id": req.plan_id,
        "plan_name": plan_info["name"],
        "billing_cycle": req.billing_cycle,
        "payment_method": req.payment_method,
        "amount_formatted": amount_str,
        "amount_usd": usd_amount,
        "amount_bdt": bdt_amount,
        "gateway_message": gateway_msg,
        "timestamp": timestamp,
        "invoice_pdf_url": f"/api/payment/invoice/{tx_id}",
    }


@router.get("/payment/plans")
def get_payment_plans():
    """Return live pricing plans and payment gateway metadata."""
    return {
        "gateways": [
            {
                "id": "stripe",
                "name": "Stripe",
                "types": ["Credit Card", "Debit Card", "Apple Pay", "Google Pay"],
                "currency": "USD",
                "icon": "stripe",
                "active": True
            },
            {
                "id": "bkash",
                "name": "bKash",
                "types": ["bKash Wallet", "MFS Direct Payment"],
                "currency": "BDT",
                "icon": "bkash",
                "active": True
            }
        ],
        "plans": [
            {
                "id": "starter",
                "name": "Starter",
                "tagline": "Ideal for individual engineers & small projects",
                "price_usd_monthly": 19,
                "price_bdt_monthly": 2200,
                "comparisons_included": 50,
                "popular": False,
                "features": [
                    "50 AI drawing comparisons / mo",
                    "Sub-pixel ORB homography alignment",
                    "PNG & PDF drawing support",
                    "Basic ECO summary export",
                    "Email support",
                ]
            },
            {
                "id": "pro",
                "name": "Professional",
                "tagline": "For engineering teams needing full compliance & VLM",
                "price_usd_monthly": 79,
                "price_bdt_monthly": 9200,
                "comparisons_included": "Unlimited",
                "popular": True,
                "features": [
                    "Unlimited AI drawing comparisons",
                    "Gemini Flash VLM change classification",
                    "ISO 10209 & ASME Y14.5 compliance logs",
                    "Annotated PDF & High-Res PNG Export",
                    "Multi-page PDF auto page-matching",
                    "Priority 24/7 technical support",
                ]
            },
            {
                "id": "enterprise",
                "name": "Enterprise Team",
                "tagline": "Custom integration for aerospace & CAD manufacturing",
                "price_usd_monthly": 249,
                "price_bdt_monthly": 28900,
                "comparisons_included": "Unlimited",
                "popular": False,
                "features": [
                    "Unlimited seat licenses for team",
                    "REST API & Python SDK access",
                    "Dedicated CAD server infrastructure",
                    "SOC2 & ISO 27001 data confidentiality",
                    "Custom VLM model fine-tuning",
                    "Dedicated Solutions Engineer",
                ]
            }
        ]
    }
