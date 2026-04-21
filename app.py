import io
import os
from datetime import date
from pathlib import Path

from flask import Flask, render_template, request, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import pypdf

app = Flask(__name__)

TEMPLATE_PDF = Path(__file__).parent / "template.pdf"
FONT = "Helvetica"
FONT_SIZE = 10

FIELD_COORDS = {
    0: {
        "client_names":      (78,  670),
        "date_of_loss":      (317, 615),
        "property_address":  (179, 601),
    },
    5: {
        "client_names":      (113, 669),
        "property_address":  (125, 647),
        "insurance_company": (153, 624),
        "policy_number":     (123, 601),
        "date_of_loss":      (205, 579),
    },
    6: {
        "client_names":      (113, 654),
        "property_address":  (125, 632),
        "insurance_company": (153, 609),
        "policy_number":     (123, 587),
        "date_of_loss":      (205, 564),
    },
    7: {
        "mortgage_company":  (205, 640),
        "loan_number":       (165, 612),
        "borrower_name":     (157, 537),
        "coborrower_name":   (344, 537),
        "borrower_address":  (157, 469),
    },
    8: {
        "client_names":      (113, 656),
        "property_address":  (125, 634),
        "insurance_company": (153, 611),
        "policy_number":     (123, 589),
        "date_of_loss":      (205, 566),
    },
}


def build_overlay(page_index: int, data: dict) -> bytes | None:
    coords = FIELD_COORDS.get(page_index)
    if not coords:
        return None

    client_names = data["client1_name"]
    if data.get("client2_name"):
        client_names += " and " + data["client2_name"]

    raw_date = data.get("date_of_loss", "")
    try:
        parsed = date.fromisoformat(raw_date)
        display_date = parsed.strftime("%m/%d/%Y")
    except ValueError:
        display_date = raw_date

    values = {
        "client_names":      client_names,
        "property_address":  data.get("property_address", ""),
        "date_of_loss":      display_date,
        "insurance_company": data.get("insurance_company", ""),
        "policy_number":     data.get("policy_number", ""),
        "mortgage_company":  data.get("mortgage_company", ""),
        "loan_number":       data.get("loan_number", ""),
        "borrower_name":     data.get("client1_name", ""),
        "coborrower_name":   data.get("coborrower_name") or data.get("client2_name", ""),
        "borrower_address":  data.get("property_address", ""),
    }

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont(FONT, FONT_SIZE)

    drew_anything = False
    for field, (x, y) in coords.items():
        if field in ("mortgage_company", "loan_number", "borrower_name", "coborrower_name", "borrower_address"):
            if not data.get("has_mortgage"):
                continue
        text = values.get(field, "")
        if text:
            c.drawString(x, y, text)
            drew_anything = True

    c.save()
    return buf.getvalue() if drew_anything else None


def fill_pdf(data: dict) -> bytes:
    reader = pypdf.PdfReader(str(TEMPLATE_PDF))
    writer = pypdf.PdfWriter()

    for page_index, page in enumerate(reader.pages):
        overlay_bytes = build_overlay(page_index, data)
        if overlay_bytes:
            overlay_reader = pypdf.PdfReader(io.BytesIO(overlay_bytes))
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = {
        "client1_name":     request.form.get("client1_name", "").strip(),
        "client2_name":     request.form.get("client2_name", "").strip(),
        "property_address": request.form.get("property_address", "").strip(),
        "date_of_loss":     request.form.get("date_of_loss", "").strip(),
        "insurance_company":request.form.get("insurance_company", "").strip(),
        "policy_number":    request.form.get("policy_number", "").strip(),
        "has_mortgage":     request.form.get("has_mortgage") == "on",
        "mortgage_company": request.form.get("mortgage_company", "").strip(),
        "loan_number":      request.form.get("loan_number", "").strip(),
        "coborrower_name":  request.form.get("coborrower_name", "").strip(),
    }

    pdf_buf = fill_pdf(data)
    safe_name = data["client1_name"].replace(" ", "_").replace("/", "-")

    return send_file(
        pdf_buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{safe_name}_retainer.pdf",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
