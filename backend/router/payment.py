import os
import uuid
import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from model.db import connect
from services.auth import get_optional_current_user
from services.bkash_service import bkash_service

router = APIRouter()

PLAN_PRICES = {
    "starter": {"usd": 19, "bdt": 2200, "name": "Starter Plan"},
    "pro": {"usd": 79, "bdt": 9200, "name": "Professional Plan"},
    "enterprise": {"usd": 249, "bdt": 28900, "name": "Enterprise Team"},
}

class BkashCreateRequest(BaseModel):
    plan_id: str = Field("pro", json_schema_extra={"example": "pro"})
    billing_cycle: str = Field("monthly", json_schema_extra={"example": "monthly"})
    payer_reference: Optional[str] = "01711111111"

class BkashExecuteRequest(BaseModel):
    paymentID: str

def _activate_user_subscription(user_id: Optional[int], email: Optional[str], plan_id: str):
    """Update user's subscription status in database upon verified payment success."""
    with connect() as conn:
        with conn.cursor() as cursor:
            if user_id:
                cursor.execute("""
                    UPDATE users SET plan_id = %s, subscription_status = 'active' WHERE user_id = %s
                """, (plan_id, user_id))
            elif email:
                cursor.execute("""
                    UPDATE users SET plan_id = %s, subscription_status = 'active' WHERE LOWER(email) = LOWER(%s)
                """, (plan_id, email))


@router.post("/bkash/create")
def create_bkash_payment(
    req: BkashCreateRequest,
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Requirement 2: Creates a payment via bKash's /tokenized/checkout/create endpoint and returns bkashURL."""
    if req.plan_id not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail="Invalid plan selected")

    plan_info = PLAN_PRICES[req.plan_id]
    multiplier = 0.8 * 12 if req.billing_cycle == "annual" else 1.0
    bdt_amount = round(plan_info["bdt"] * multiplier)
    invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"

    user_id = current_user.get("user_id") if current_user else None
    user_email = current_user.get("email") if current_user else "guest@engineeringdrawings.com"

    # Call bKash service create payment
    bkash_resp = bkash_service.create_payment(
        amount_bdt=bdt_amount,
        invoice_number=invoice_number,
        payer_reference=req.payer_reference or "01711111111"
    )

    payment_id = bkash_resp["paymentID"]
    bkash_url = bkash_resp["bkashURL"]

    # Store pending payment record in DB
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO payments (payment_id, user_id, user_email, plan_id, billing_cycle, amount_cents, currency, status, stripe_intent_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
            """, (payment_id, user_id, user_email, req.plan_id, req.billing_cycle, int(bdt_amount * 100), "bdt", invoice_number))

    return {
        "status": "success",
        "paymentID": payment_id,
        "bkashURL": bkash_url,
        "statusCode": bkash_resp.get("statusCode", "0000"),
        "statusMessage": bkash_resp.get("statusMessage", "Successful"),
        "invoiceNumber": invoice_number,
        "amount_bdt": bdt_amount,
    }


@router.get("/bkash/callback")
@router.post("/bkash/callback")
def bkash_callback(
    paymentID: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Requirement 4: Receives bKash's redirect callback with paymentID and status."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    
    if not paymentID or status != "success":
        redirect_url = f"{frontend_url}/payment-callback?status=failed&paymentID={paymentID or ''}"
        return RedirectResponse(url=redirect_url)

    # Redirect to frontend callback handler to trigger independent backend verification
    redirect_url = f"{frontend_url}/payment-callback?status=success&paymentID={paymentID}"
    return RedirectResponse(url=redirect_url)


@router.post("/bkash/execute")
def execute_bkash_payment(
    req: BkashExecuteRequest,
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Requirement 5 & 7: Calls bKash execute endpoint and independently queries status to verify before updating database."""
    payment_id = req.paymentID
    if not payment_id:
        raise HTTPException(status_code=400, detail="Missing paymentID parameter")

    # Fetch pending payment from database
    payment_record = None
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM payments WHERE payment_id = %s", (payment_id,))
            row = cursor.fetchone()
            if row:
                payment_record = dict(row)

    user_id = current_user.get("user_id") if current_user else (payment_record.get("user_id") if payment_record else None)
    email = current_user.get("email") if current_user else (payment_record.get("user_email") if payment_record else None)
    plan_id = payment_record.get("plan_id", "pro") if payment_record else "pro"
    billing_cycle = payment_record.get("billing_cycle", "monthly") if payment_record else "monthly"

    try:
        # Independently verify via bKash execute + status query endpoint
        verification = bkash_service.verify_and_execute_checkout(payment_id)
        trx_id = verification["trxID"]

        # Update DB payments record to succeeded
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE payments SET status = 'succeeded', updated_at = NOW() WHERE payment_id = %s
                """, (payment_id,))

        # Update DB users subscription status
        _activate_user_subscription(user_id, email, plan_id)

        plan_info = PLAN_PRICES.get(plan_id, {"usd": 79, "bdt": 9200, "name": "Professional Plan"})
        multiplier = 0.8 * 12 if billing_cycle == "annual" else 1.0
        bdt_amount = round(plan_info["bdt"] * multiplier)
        usd_amount = round(plan_info["usd"] * multiplier, 2)

        return {
            "status": "success",
            "message": f"Payment independently verified via bKash API. Subscription activated for {plan_info['name']}.",
            "transaction_id": trx_id,
            "paymentID": payment_id,
            "plan_id": plan_id,
            "plan_name": plan_info["name"],
            "billing_cycle": billing_cycle,
            "payment_method": "bkash",
            "amount_formatted": f"৳{bdt_amount:,} BDT",
            "amount_bdt": bdt_amount,
            "amount_usd": usd_amount,
            "gateway_message": f"Verified via bKash Tokenized Checkout (TRX: {trx_id})",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "invoice_pdf_url": f"/api/payment/invoice/{trx_id}",
        }
    except Exception as e:
        print(f"[bKash Verification Error]: {e}")
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE payments SET status = 'failed', updated_at = NOW() WHERE payment_id = %s
                """, (payment_id,))
        raise HTTPException(status_code=400, detail=f"bKash payment verification failed: {str(e)}")


@router.get("/payment/plans")
def get_payment_plans():
    """Return live pricing plans and bKash payment gateway metadata."""
    return {
        "gateways": [
            {
                "id": "bkash",
                "name": "bKash Tokenized Checkout",
                "types": ["bKash Wallet", "MFS Tokenized Payment", "Sandbox Tokenized Gateway"],
                "currency": "BDT",
                "icon": "bkash",
                "active": True,
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
                ],
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
                ],
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
                ],
            },
        ],
    }
