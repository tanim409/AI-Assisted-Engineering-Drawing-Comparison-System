import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_payment_plans():
    response = client.get("/api/payment/plans")
    assert response.status_code == 200
    data = response.json()
    assert "gateways" in data
    assert "plans" in data
    assert len(data["plans"]) == 3
    gateway_ids = [g["id"] for g in data["gateways"]]
    assert "stripe" in gateway_ids
    assert "bkash" in gateway_ids

def test_stripe_checkout():
    payload = {
        "plan_id": "pro",
        "billing_cycle": "monthly",
        "payment_method": "stripe",
        "stripe_details": {
            "cardholder_name": "Test User",
            "card_number": "4242 4242 4242 4242",
            "exp_month": "12",
            "exp_year": "28",
            "cvc": "123"
        }
    }
    response = client.post("/api/payment/checkout", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "success"
    assert res["plan_id"] == "pro"
    assert res["payment_method"] == "stripe"
    assert res["transaction_id"].startswith("tx_str_")

def test_bkash_checkout():
    payload = {
        "plan_id": "starter",
        "billing_cycle": "annual",
        "payment_method": "bkash",
        "bkash_details": {
            "phone_number": "01712345678",
            "otp": "123456",
            "pin": "12345"
        }
    }
    response = client.post("/api/payment/checkout", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "success"
    assert res["plan_id"] == "starter"
    assert res["payment_method"] == "bkash"
    assert res["transaction_id"].startswith("TRX")
