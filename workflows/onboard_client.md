# Workflow: Onboard New Client

**Objective:** Collect client data, generate a pre-filled retainer PDF, and log the client to the tracking sheet.

**Required inputs:**
- Client name(s), property address, date of loss, insurance company, policy number
- Mortgage info (if applicable)

**Template:** `ILG PLG 2033 Retainer (v 3-26-2026).pdf` must be in the project root.

---

## Steps

### 1. Collect client data
Open `tools/collect_client_intake.html` in any browser (double-click the file).

Fill in all required fields:
- Client 1 name (required)
- Client 2 name (optional — check "Add a second client")
- Property address
- Date of Loss
- Insurance company & policy number
- Mortgage info (optional — check "Property has a mortgage")

Click **Generate Contract Data**. A file named `client_intake_<name>.json` will download automatically.

Move that file into the `.tmp/` folder in the project root.

---

### 2. Generate the filled PDF
```bash
python tools/fill_contract_pdf.py .tmp/client_intake_Jane_Doe.json
```

Output: `.tmp/Jane_Doe_retainer_filled.pdf`

Open the PDF and confirm all data fields are populated on pages 1, 6, 7, 8 (if mortgage), and 9. Signature lines should be blank — those are for DocuSign.

> **If field positions look off:** Run probe mode to see a coordinate grid, then adjust `FIELD_COORDS` in `fill_contract_pdf.py`:
> ```bash
> python tools/fill_contract_pdf.py --probe
> ```
> This writes `.tmp/probe_grid.pdf` — open it and read the (x, y) of each blank field.

---

### 3. Log to Google Sheet
```bash
python tools/export_intake_to_sheets.py .tmp/client_intake_Jane_Doe.json
```

This appends a row to the **Client Intake** sheet (ID in `.env` as `INTAKE_SHEET_ID`).

> **First time setup:** Run `python tools/google_auth.py` to authorize Google access. Requires `credentials.json` in the project root (download from Google Cloud Console).

---

### 4. Upload to DocuSign
Upload `.tmp/<name>_retainer_filled.pdf` to DocuSign manually. Add signature, name, and date fields for the client(s) using DocuSign's template editor.

---

## Edge cases

| Situation | Handling |
|---|---|
| No second client | Leave Client 2 blank — the "and ..." portion is omitted from the PDF |
| No mortgage | Uncheck the mortgage toggle — page 8 fields are left blank |
| Template PDF missing | Script exits with a clear error. Place the PDF in project root or set `CONTRACT_TEMPLATE_PATH` in `.env` |
| Field positions wrong after template update | Re-run `--probe` and recalibrate `FIELD_COORDS` in `fill_contract_pdf.py` |
