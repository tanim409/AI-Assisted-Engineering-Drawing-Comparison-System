import cv2
import fitz
import numpy as np

from model.report_db import init_db
from services.report_data import complete_report, init_report, save_report_page


def _png(width=200, height=160):
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def _change(x, y, w, h, category):
    return {"bbox": {"x": x, "y": y, "w": w, "h": h}, "classification": {"category": category}}


def _store_report(report_id, pages):
    init_db()
    init_report(report_id, len(pages), {}, None, False, None, f"hash-{report_id}")
    for number, changes in enumerate(pages, start=1):
        save_report_page(report_id, {
            "page_number": number,
            "page_status": "matched",
            "changes": changes,
            "annotated_source_png": _png(),
        })
    complete_report(report_id, len(pages), {}, None, False, None)


def test_single_page_png_has_correct_boxes_and_is_valid(client):
    _store_report("annotated-single", [[
        _change(20, 30, 50, 40, "addition"),
        _change(100, 80, 40, 30, "removal"),
    ]])
    response = client.get("/api/reports/annotated-single/annotated?format=png")
    assert response.status_code == 200
    image = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    assert tuple(image[30, 20]) == (0, 200, 0)  # addition = green (BGR)
    assert tuple(image[80, 100]) == (0, 0, 255)  # removal = red (BGR)


def test_multi_page_export_is_pdf_in_page_order(client):
    _store_report("annotated-multi", [
        [_change(20, 30, 50, 40, "addition")],
        [_change(80, 50, 40, 30, "dimension_change")],
    ])
    response = client.get("/api/reports/annotated-multi/annotated?format=pdf")
    assert response.status_code == 200
    document = fitz.open(stream=response.content, filetype="pdf")
    assert len(document) == 2
    document.close()


def test_multi_page_png_selects_requested_page(client):
    _store_report("annotated-page-select", [
        [_change(20, 30, 50, 40, "addition")],
        [_change(80, 50, 40, 30, "removal")],
    ])
    response = client.get("/api/reports/annotated-page-select/annotated?format=png&page=2")
    assert response.status_code == 200
    image = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    assert tuple(image[50, 80]) == (0, 0, 255)


def test_zero_change_export_is_valid_unannotated_png(client):
    _store_report("annotated-empty", [[]])
    response = client.get("/api/reports/annotated-empty/annotated?format=png")
    assert response.status_code == 200
    image = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    assert tuple(image[50, 50]) == (255, 255, 255)
