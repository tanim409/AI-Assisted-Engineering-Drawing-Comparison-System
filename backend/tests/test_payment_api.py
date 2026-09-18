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
    assert "bkash" in gateway_ids
    assert "stripe" not in gateway_ids

def test_bkash_create():
    payload = {
        "plan_id": "pro",
        "billing_cycle": "monthly",
        "payer_reference": "01711111111"
    }
    response = client.post("/api/bkash/create", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "success"
    assert "paymentID" in res
    assert "bkashURL" in res
    assert res["amount_bdt"] == 9200

def test_bkash_execute():
    # 1. First create paymentID
    create_res = client.post("/api/bkash/create", json={"plan_id": "starter", "billing_cycle": "monthly"})
    assert create_res.status_code == 200
    pid = create_res.json()["paymentID"]

    # 2. Execute payment (runs execute + independent status query verification)
    exec_res = client.post("/api/bkash/execute", json={"paymentID": pid})
    assert exec_res.status_code == 200
    res = exec_res.json()
    assert res["status"] == "success"
    assert res["paymentID"] == pid
    assert res["payment_method"] == "bkash"
    assert "transaction_id" in res

