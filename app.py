import io
import os
import zipfile
from datetime import date, datetime
from pathlib import Path

from flask import Flask, render_template, request, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import pypdf

app = Flask(__name__)

TEMPLATE_PDF = Path(__file__).parent / "template.pdf"
ILG_LOGO   = Path(__file__).parent / "ilg_logo.png"
TPLG_LOGO  = Path(__file__).parent / "tplg_logo.png"
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


def fill_contract_pdf(data: dict) -> io.BytesIO:
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


def build_notes_pdf(data: dict) -> io.BytesIO:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    W, H = letter

    MARGIN = 60
    y = H - 60

    def draw_header():
        nonlocal y
        # Logos — ILG left, TPLG right
        ilg_h, ilg_w = 40, int(40 * 228 / 157)   # ~58pt wide
        tplg_h, tplg_w = 40, int(40 * 266 / 81)  # ~131pt wide
        logo_y = y - ilg_h + 8
        c.drawImage(str(ILG_LOGO),  MARGIN, logo_y, width=ilg_w,  height=ilg_h,  mask='auto')
        c.drawImage(str(TPLG_LOGO), W - MARGIN - tplg_w, logo_y + 4, width=tplg_w, height=tplg_h - 8, mask='auto')
        y -= ilg_h + 6

        # Title
        c.setFillColor(colors.HexColor("#003087"))
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(W / 2, y, "Client Intake Questionnaire")
        y -= 18

        # Subheader
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#555555"))

        client_names = data["client1_name"]
        if data.get("client2_name"):
            client_names += " and " + data["client2_name"]

        raw_date = data.get("date_of_loss", "")
        try:
            display_date = date.fromisoformat(raw_date).strftime("%m/%d/%Y")
        except ValueError:
            display_date = raw_date

        c.drawString(MARGIN, y - 22, f"Client: {client_names}")
        c.drawString(MARGIN, y - 34, f"Property: {data.get('property_address', '')}")
        c.drawString(MARGIN + 300, y - 22, f"Date of Loss: {display_date}")
        c.drawString(MARGIN + 300, y - 34, f"Prepared: {datetime.now().strftime('%m/%d/%Y')}")
        y -= 55
        # Divider
        c.setStrokeColor(colors.HexColor("#003087"))
        c.setLineWidth(1.5)
        c.line(MARGIN, y, W - MARGIN, y)
        y -= 18

    def draw_qa(question, answer, note=None):
        nonlocal y, c
        if y < 100:
            c.showPage()
            y = H - 60
            c.setStrokeColor(colors.HexColor("#003087"))
            c.setLineWidth(0.5)
            c.line(MARGIN, H - 55, W - MARGIN, H - 55)
            y = H - 70

        # Question
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#1a1a2e"))
        c.drawString(MARGIN, y, question)
        y -= 15

        # Answer
        c.setFont("Helvetica", 10)
        ans_color = colors.HexColor("#1a7a4a") if answer.lower() in ("yes", "no") else colors.HexColor("#1a1a2e")
        c.setFillColor(ans_color)
        c.drawString(MARGIN + 12, y, answer)
        y -= 12

        # Optional note
        if note:
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColor(colors.HexColor("#555555"))
            # Wrap long notes
            max_w = W - 2 * MARGIN - 24
            words = note.split()
            line = ""
            for word in words:
                test = (line + " " + word).strip()
                if c.stringWidth(test, "Helvetica-Oblique", 9) < max_w:
                    line = test
                else:
                    c.drawString(MARGIN + 24, y, line)
                    y -= 12
                    line = word
            if line:
                c.drawString(MARGIN + 24, y, line)
                y -= 12

        # Light separator
        c.setStrokeColor(colors.HexColor("#e8edf5"))
        c.setLineWidth(0.5)
        c.line(MARGIN, y, W - MARGIN, y)
        y -= 10

    def draw_description(question, text):
        """Draw a question with fully wrapped multi-paragraph body text."""
        nonlocal y, c
        if y < 100:
            c.showPage()
            y = H - 60
            c.setStrokeColor(colors.HexColor("#003087"))
            c.setLineWidth(0.5)
            c.line(MARGIN, H - 55, W - MARGIN, H - 55)
            y = H - 70

        # Question label
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#1a1a2e"))
        c.drawString(MARGIN, y, question)
        y -= 15

        max_w = W - 2 * MARGIN - 12
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#1a1a2e"))

        for paragraph in (text or "—").split("\n"):
            words = paragraph.split()
            if not words:
                y -= 8
                continue
            line = ""
            for word in words:
                test = (line + " " + word).strip()
                if c.stringWidth(test, "Helvetica", 10) <= max_w:
                    line = test
                else:
                    if y < 80:
                        c.showPage()
                        y = H - 60
                        c.setFont("Helvetica", 10)
                        c.setFillColor(colors.HexColor("#1a1a2e"))
                    c.drawString(MARGIN + 12, y, line)
                    y -= 14
                    line = word
            if line:
                if y < 80:
                    c.showPage()
                    y = H - 60
                    c.setFont("Helvetica", 10)
                    c.setFillColor(colors.HexColor("#1a1a2e"))
                c.drawString(MARGIN + 12, y, line)
                y -= 14
            y -= 4  # paragraph gap

        c.setStrokeColor(colors.HexColor("#e8edf5"))
        c.setLineWidth(0.5)
        c.line(MARGIN, y, W - MARGIN, y)
        y -= 10

    draw_header()

    yn = lambda key: "Yes" if data.get(key) == "yes" else "No"

    draw_qa("Did this incident cause property damage?", yn("property_damage"))

    claim_ans = yn("claim_number_assigned")
    claim_note = f"Claim #: {data.get('claim_number', '')}" if data.get("claim_number_assigned") == "yes" and data.get("claim_number") else None
    draw_qa("Have you been assigned a claim number?", claim_ans, claim_note)

    draw_qa("Incident address same as policyholder's address?", yn("same_address"))
    draw_qa("Do you plan on selling this property in the next year?", yn("selling_next_year"))
    draw_qa("Tenants in the property?", yn("tenants"))

    mortgage_ans = yn("has_mortgage_q")
    mortgage_note = f"Mortgage Company: {data.get('mortgage_company', '')}" if data.get("has_mortgage_q") == "yes" and data.get("mortgage_company") else None
    draw_qa("Mortgage on the property?", mortgage_ans, mortgage_note)

    description = data.get("description", "").strip()
    draw_description("Client's description of what happened:", description)

    draw_qa("Contents damage?", yn("contents_damage"))
    draw_qa("Additional Living Expenses or Loss of Rent?", yn("ale_loss_of_rent"))

    repairs_ans = yn("repairs_performed")
    repairs_note = data.get("repairs_details", "").strip() or None
    draw_qa("Repairs performed?", repairs_ans, repairs_note)

    draw_qa("Prior claims?", yn("prior_claims"))

    hoa_ans = yn("hoa")
    hoa_note = f"HOA Name: {data.get('hoa_name', '')}" if data.get("hoa") == "yes" and data.get("hoa_name") else None
    draw_qa("HOA?", hoa_ans, hoa_note)

    if data.get("referred_by"):
        draw_qa("Referred By:", data["referred_by"])

    c.save()
    buf.seek(0)
    return buf


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = {
        # Contract fields
        "client1_name":          request.form.get("client1_name", "").strip(),
        "client2_name":          request.form.get("client2_name", "").strip(),
        "property_address":      request.form.get("property_address", "").strip(),
        "date_of_loss":          request.form.get("date_of_loss", "").strip(),
        "insurance_company":     request.form.get("insurance_company", "").strip(),
        "policy_number":         request.form.get("policy_number", "").strip(),
        "has_mortgage":          request.form.get("has_mortgage_q") == "yes",
        "mortgage_company":      request.form.get("mortgage_company", "").strip(),
        "loan_number":           request.form.get("loan_number", "").strip(),
        "coborrower_name":       request.form.get("coborrower_name", "").strip(),
        # Questionnaire fields
        "property_damage":       request.form.get("property_damage", ""),
        "claim_number_assigned": request.form.get("claim_number_assigned", ""),
        "claim_number":          request.form.get("claim_number", "").strip(),
        "same_address":          request.form.get("same_address", ""),
        "selling_next_year":     request.form.get("selling_next_year", ""),
        "tenants":               request.form.get("tenants", ""),
        "has_mortgage_q":        request.form.get("has_mortgage_q", ""),
        "description":           request.form.get("description", "").strip(),
        "contents_damage":       request.form.get("contents_damage", ""),
        "ale_loss_of_rent":      request.form.get("ale_loss_of_rent", ""),
        "repairs_performed":     request.form.get("repairs_performed", ""),
        "repairs_details":       request.form.get("repairs_details", "").strip(),
        "prior_claims":          request.form.get("prior_claims", ""),
        "hoa":                   request.form.get("hoa", ""),
        "hoa_name":              request.form.get("hoa_name", "").strip(),
        "referred_by":           request.form.get("referred_by", "").strip(),
    }

    contract_pdf = fill_contract_pdf(data)
    notes_pdf = build_notes_pdf(data)

    safe_name = data["client1_name"].replace(" ", "_").replace("/", "-")

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{safe_name}_retainer.pdf", contract_pdf.read())
        zf.writestr(f"{safe_name}_intake_notes.pdf", notes_pdf.read())
    zip_buf.seek(0)

    return send_file(
        zip_buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{safe_name}_ILG_intake.zip",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

