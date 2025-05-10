# Backend/app.py

from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
FRONT_DIR = BASE_DIR.parent / "frontend"
TEMP_DIR  = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(FRONT_DIR),
    static_folder=str(FRONT_DIR),
    static_url_path=""
)
CORS(app)

# ─────────── “BD” en memoria y constantes de factura ──────────────────────────
patients = []
DOCTOR   = "DR. FRANCISCO ENRIQUE CABRERA PORTIELES"
SPEC     = "NEUROFISIOLOGO CLINICO"
LICENSE  = "RM0307 - CC 1047488543"

def auto_price(idx: int) -> int:
    return 100_000 if idx < 20 else 70_000

def clean(name: str) -> str:
    return Path(name).stem.replace("_", " ").title()

def format_money(value: int) -> str:
    return f"₱{value:,.0f}".replace(",", ".")

# ─────────── Generador de Word con conteo de estudios ────────────────────────
def docx_invoice(number: str) -> Path:
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # encabezado
    hdr = doc.add_paragraph()
    hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run  = hdr.add_run(DOCTOR + "\n")
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0, 51, 102)
    sub  = hdr.add_run(SPEC + "\n")
    sub.font.size = Pt(12)
    sub.font.color.rgb = RGBColor(0, 51, 102)
    lic  = hdr.add_run(LICENSE + "\n\n")
    lic.italic = True
    lic.font.size = Pt(10)
    lic.font.color.rgb = RGBColor(0, 51, 102)

    # línea de estudios
    count = len(patients)
    p_count = doc.add_paragraph()
    p_count.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cnt_run = p_count.add_run(
        f"SE REALIZÓ INFORME Y PROCESAMIENTO DE LA CANTIDAD DE ESTUDIOS: {count}\n"
        "ESTUDIOS DE POLISOMNOGRAFÍA\n\n"
    )
    cnt_run.bold = True
    cnt_run.font.size = Pt(11)
    cnt_run.font.color.rgb = RGBColor(0, 51, 102)

    # factura y fecha
    doc.add_paragraph(f"FACTURA N°: {number}", style='Heading 1').runs[0].bold = True
    doc.add_paragraph(f"Fecha: {datetime.now():%d/%m/%Y %H:%M}")
    doc.add_paragraph()

    # tabla
    table = doc.add_table(rows=1, cols=3)
    table.style     = 'Light List Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "No."
    hdr_cells[1].text = "PACIENTE"
    hdr_cells[2].text = "VALOR"
    for idx, p in enumerate(patients, 1):
        row = table.add_row().cells
        row[0].text = str(idx)
        row[1].text = p['name']
        row[2].text = format_money(p['price'])

    # total
    doc.add_paragraph()
    total = sum(p['price'] for p in patients)
    tot_p = doc.add_paragraph()
    tot_p.paragraph_format.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    run_tot = tot_p.add_run(f"TOTAL: {format_money(total)}")
    run_tot.bold = True
    run_tot.font.size = Pt(12)

    fn = TEMP_DIR / f"Factura_{number}.docx"
    doc.save(fn)
    return fn

# ─────────── Generador de PDF con paginación y único encabezado ─────────────
def generate_pdf(number: str) -> Path:
    pdf_path = TEMP_DIR / f"Factura_{number}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    w, h = letter

    def draw_table_header(y0):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(72, y0, "No.")
        c.drawString(120, y0, "PACIENTE")
        c.drawRightString(w-72, y0, "VALOR")
        c.line(72, y0-5, w-72, y0-5)

    def draw_full_header():
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0,51/255,102/255)
        c.drawCentredString(w/2, h-50, DOCTOR)
        c.setFont("Helvetica", 12)
        c.drawCentredString(w/2, h-70, SPEC)
        c.drawCentredString(w/2, h-85, LICENSE)

        count = len(patients)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(w/2, h-105,
            f"SE REALIZÓ INFORME Y PROCESAMIENTO DE LA CANTIDAD DE ESTUDIOS: {count}"
        )
        c.drawCentredString(w/2, h-120, "ESTUDIOS DE POLISOMNOGRAFÍA")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, h-150, f"FACTURA N°: {number}")
        c.setFont("Helvetica", 11)
        c.drawString(72, h-170, f"Fecha: {datetime.now():%d/%m/%Y %H:%M}")

    # layout
    row_h    = 18
    max_rows = int((h - 260) / row_h)
    y        = h - 225

    # primera página
    draw_full_header()
    draw_table_header(h-200)

    for idx, p in enumerate(patients, 1):
        if (idx-1) and (idx-1) % max_rows == 0:
            c.showPage()
            draw_table_header(h-50)
            y = h - 80
        c.setFont("Helvetica", 10)
        c.drawString(72, y, str(idx))
        c.drawString(120, y, p['name'])
        c.drawRightString(w-72, y, format_money(p['price']))
        y -= row_h

    # subtotales
    subtotal = sum(p['price'] for p in patients)
    if y < 100:
        c.showPage()
        draw_table_header(h-50)
        y = h - 80

    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(w-72, y - 20, f"SUBTOTAL: {format_money(subtotal)}")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w-72, y - 40, f"TOTAL:    {format_money(subtotal)}")

    c.save()
    return pdf_path

# ─────────── Endpoints ───────────────────────────────────────────────────────
@app.route("/api/patients", methods=["GET", "POST"])
def patients_api():
    if request.method == "POST" and "files" in request.files:
        new = []
        for f in request.files.getlist("files"):
            if f.filename.lower().endswith((".doc", ".docx", ".pdf")):
                idx = len(patients) + len(new)
                new.append({
                    "id":    idx + 1,
                    "name":  clean(f.filename),
                    "price": auto_price(idx)
                })
        patients.extend(new)
        return jsonify(success=True, patients=new)

    if request.method == "POST":
        data = request.get_json(force=True) or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify(error="Nombre requerido"), 400
        idx   = len(patients)
        price = int(data.get("price") or auto_price(idx))
        if idx < 20:
            price = 100_000
        p = {"id": idx + 1, "name": name, "price": price}
        patients.append(p)
        return jsonify(p), 201

    subtotal = sum(p["price"] for p in patients)
    return jsonify(patients=patients, count=len(patients), subtotal=subtotal)

@app.route("/api/patients/<int:pid>", methods=["PUT", "DELETE"])
def one_patient(pid: int):
    p = next((x for x in patients if x["id"] == pid), None)
    if not p:
        return "", 404

    if request.method == "DELETE":
        patients.remove(p)
        for i, obj in enumerate(patients, start=1):
            obj["id"] = i
        return "", 204

    data = request.get_json(force=True) or {}
    p["name"] = data.get("name", p["name"]).strip()

    if "price" in data:
        try:
            p["price"] = int(data["price"])
        except ValueError:
            return jsonify(error="Precio inválido"), 400
    else:
        p["price"] = auto_price(p["id"] - 1)

    return jsonify(p)

@app.route("/api/clear", methods=["DELETE"])
def clear_list():
    patients.clear()
    return "", 204

@app.route("/api/invoice/<fmt>", methods=["POST"])
def invoice(fmt: str):
    if not patients:
        return jsonify(error="No hay pacientes para facturar"), 400
    data = request.get_json(force=True) or {}
    num  = data.get("invoice_number", f"FAC-{datetime.now():%Y%m%d%H%M%S}")
    path = docx_invoice(num) if fmt == "word" else generate_pdf(num)
    return send_file(path, as_attachment=True)

@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")

# ─────────────────────────────
# INICIO APLICACIÓN (HOST/PORT desde env)
# ─────────────────────────────
if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    app.run(host=host, port=port, debug=True)
