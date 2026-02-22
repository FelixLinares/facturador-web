from pathlib import Path
from datetime import datetime
from collections import Counter
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
FRONT_DIR = BASE_DIR.parent / "frontend"
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(FRONT_DIR),
    static_folder=str(FRONT_DIR),
    static_url_path=""
)
CORS(app)

# ─────────── “BD” en memoria ──────────────────────────────────────────────────
patients = []
DOCTOR  = "DR. FRANCISCO ENRIQUE CABRERA PORTIELES"
SPEC    = "NEUROFISIOLOGO CLINICO"
LICENSE = "RM0307 - CC 1047488543"

# ─────────── Utilidades ──────────────────────────────────────────────────────
def clean(name: str) -> str:
    return Path(name).stem.replace("_", " ").title()

def format_money(value: int) -> str:
    return f"₱{value:,.0f}".replace(",", ".")

# ─────────── Generador Word (ORIGINAL, NO TOCADO) ─────────────────────────────
def docx_invoice(number: str) -> Path:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    hdr = doc.add_paragraph()
    hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = hdr.add_run(DOCTOR + "\n")
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0, 51, 102)
    doc.add_paragraph(SPEC).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(LICENSE).alignment = WD_ALIGN_PARAGRAPH.CENTER

    count = len(patients)
    doc.add_paragraph(
        f"SE REALIZÓ INFORME Y PROCESAMIENTO DE LA CANTIDAD DE ESTUDIOS: {count}\n"
        "ESTUDIOS DE POLISOMNOGRAFÍA\n"
    ).alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(f"FACTURA N°: {number}", style='Heading 1')
    doc.add_paragraph(f"Fecha: {datetime.now():%d/%m/%Y %H:%M}")

    table = doc.add_table(rows=1, cols=3)
    table.style = 'Light List Accent 1'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "No."
    hdr_cells[1].text = "PACIENTE"
    hdr_cells[2].text = "VALOR"

    for i, p in enumerate(patients, 1):
        row = table.add_row().cells
        row[0].text = str(i)
        row[1].text = p["name"]
        row[2].text = format_money(p["price"])

    total = sum(p["price"] for p in patients)
    doc.add_paragraph(f"TOTAL: {format_money(total)}").runs[0].bold = True

    path = TEMP_DIR / f"Factura_{number}.docx"
    doc.save(path)
    return path

# ─────────── Generador PDF (BONITO + SUBTOTALES CORREGIDOS) ───────────────────
def generate_pdf(number: str) -> Path:
    pdf_path = TEMP_DIR / f"Factura_{number}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    w, h = letter

    def draw_header():
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0, 51/255, 102/255)
        c.drawCentredString(w/2, h-50, DOCTOR)

        c.setFont("Helvetica", 12)
        c.drawCentredString(w/2, h-70, SPEC)
        c.drawCentredString(w/2, h-85, LICENSE)

        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(
            w/2, h-105,
            f"SE REALIZÓ INFORME Y PROCESAMIENTO DE LA CANTIDAD DE ESTUDIOS: {len(patients)}"
        )
        c.drawCentredString(w/2, h-120, "ESTUDIOS DE POLISOMNOGRAFÍA")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, h-150, f"FACTURA N°: {number}")
        c.setFont("Helvetica", 11)
        c.drawString(72, h-170, f"Fecha: {datetime.now():%d/%m/%Y %H:%M}")

        c.line(72, h-180, w-72, h-180)

    def draw_table_header(y):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(72, y, "No.")
        c.drawString(120, y, "PACIENTE")
        c.drawRightString(w-72, y, "VALOR")
        c.line(72, y-4, w-72, y-4)

    draw_header()
    y = h - 205
    row_h = 18
    max_rows = int((y - 160) / row_h)

    draw_table_header(y)
    y -= 20

    for i, p in enumerate(patients, 1):
        if i > 1 and (i - 1) % max_rows == 0:
            c.showPage()
            y = h - 80
            draw_table_header(y)
            y -= 20

        c.setFont("Helvetica", 10)
        c.drawString(72, y, str(i))
        c.drawString(120, y, p["name"])
        c.drawRightString(w-72, y, format_money(p["price"]))
        y -= row_h

    # ───── SUBTOTALES POR PRECIO (SIN ₱) ─────
    price_groups = Counter(p["price"] for p in patients)

    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(72, y, "SUBTOTAL:")
    y -= 18

    c.setFont("Helvetica", 10)
    for price, qty in sorted(price_groups.items(), reverse=True):
        subtotal = price * qty
        c.drawString(
            72,
            y,
            f"{qty} × {price:,.0f}".replace(",", ".") +
            f" = {subtotal:,.0f}".replace(",", ".")
        )
        y -= 16

    total = sum(p["price"] for p in patients)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w-72, y-10, f"TOTAL: {format_money(total)}")

    c.save()
    return pdf_path

# ─────────── API ─────────────────────────────────────────────────────────────
@app.route("/api/patients", methods=["GET", "POST"])
def patients_api():
    if request.method == "POST" and "files" in request.files:
        new = []
        for f in request.files.getlist("files"):
            if f.filename.lower().endswith((".doc", ".docx", ".pdf")):
                idx = len(patients) + len(new)
                price = 100_000 if idx < 20 else 70_000
                new.append({
                    "id": idx + 1,
                    "name": clean(f.filename),
                    "price": price
                })
        patients.extend(new)
        return jsonify(success=True)

    if request.method == "POST":
        data = request.get_json(force=True) or {}
        if not data.get("name"):
            return jsonify(error="Nombre requerido"), 400
        p = {
            "id": len(patients) + 1,
            "name": data["name"].strip(),
            "price": int(data.get("price", 100_000))
        }
        patients.append(p)
        return jsonify(p), 201

    return jsonify(
        patients=patients,
        count=len(patients),
        subtotal=sum(p["price"] for p in patients)
    )

@app.route("/api/patients/<int:pid>", methods=["PUT", "DELETE"])
def one_patient(pid):
    p = next((x for x in patients if x["id"] == pid), None)
    if not p:
        return "", 404

    if request.method == "DELETE":
        patients.remove(p)
        for i, obj in enumerate(patients, 1):
            obj["id"] = i
        return "", 204

    data = request.get_json(force=True) or {}
    if "name" in data:
        p["name"] = data["name"].strip()
    if "price" in data:
        p["price"] = int(data["price"])
    return jsonify(p)

@app.route("/api/clear", methods=["DELETE"])
def clear():
    patients.clear()
    return "", 204

@app.route("/api/invoice/<fmt>", methods=["POST"])
def invoice(fmt):
    if not patients:
        return jsonify(error="No hay pacientes"), 400
    num = request.json.get("invoice_number")
    path = docx_invoice(num) if fmt == "word" else generate_pdf(num)
    return send_file(path, as_attachment=True)

@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")

# ─────────── 🔥 FIX RENDER (ÚNICO CAMBIO) 🔥 ───────────
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
