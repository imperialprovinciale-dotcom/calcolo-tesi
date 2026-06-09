import fitz  # PyMuPDF
from PIL import Image
import io
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- LE TUE FUNZIONI ORIGINALI ---
def is_grayscale(image):
    if image.mode not in ("L", "RGB"): return False
    if image.mode == "L": return True
    rgb = image.convert("RGB")
    for r, g, b in rgb.getdata():
        if r != g or g != b: return False
    return True

def has_color_text(page):
    text_colors = page.get_text("dict")["blocks"]
    for block in text_colors:
        if 'lines' in block:
            for line in block['lines']:
                for span in line['spans']:
                    color = span['color']
                    if color and isinstance(color, int):
                        r, g, b = (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF
                        if not (abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30):
                            return True
    return False

def has_color_images(page, doc):
    for img in page.get_images(full=True):
        if fitz.Pixmap(doc, img[0]).n >= 4:
            return True
    return False

def analyze_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    color_pages, bw_pages = 0, 0
    color_page_numbers = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        img = Image.open(io.BytesIO(page.get_pixmap().tobytes("png")))
        
        if is_grayscale(img) and not has_color_text(page) and not has_color_images(page, doc):
            bw_pages += 1
        else:
            color_pages += 1
            color_page_numbers.append(page_num + 1)

    costo_color = color_pages * 0.35
    costo_bw = bw_pages * 0.08
    
    return {
        "pagine_colore": color_pages,
        "dettaglio_colore": color_page_numbers,
        "pagine_bn": bw_pages,
        "totale_pagine": len(doc),
        "totale_euro": round(costo_color + costo_bw, 2)
    }

# --- SERVER FLASK ---
app = Flask(__name__)
CORS(app)

@app.route('/calcola', methods=['POST'])
def calcola():
    if 'file' not in request.files:
        return jsonify({"errore": "Nessun file caricato"}), 400
    
    file = request.files['file']
    temp_path = f"temp_{file.filename}"
    file.save(temp_path)
    
    try:
        risultato = analyze_pdf(temp_path)
    except Exception as e:
        return jsonify({"errore": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    return jsonify(risultato)

if __name__ == '__main__':
    app.run(port=5000)
