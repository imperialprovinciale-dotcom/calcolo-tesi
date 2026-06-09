import fitz  # PyMuPDF
from PIL import Image, ImageChops
import io
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

def is_grayscale(image):
    if image.mode == "L": return True
    rgb = image.convert("RGB")
    r, g, b = rgb.split()
    # Metodo ultra veloce per controllare i pixel
    diff_rg = ImageChops.difference(r, g).getextrema()
    diff_gb = ImageChops.difference(g, b).getextrema()
    return diff_rg[1] == 0 and diff_gb[1] == 0

def has_color_text(page):
    try:
        text_colors = page.get_text("dict")["blocks"]
        for block in text_colors:
            if 'lines' in block:
                for line in block['lines']:
                    for span in line['spans']:
                        color = span.get('color')
                        if color and isinstance(color, int):
                            r, g, b = (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF
                            if not (abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30):
                                return True
    except: pass
    return False

def has_color_images(page, doc):
    for img in page.get_images(full=True):
        if fitz.Pixmap(doc, img[0]).n >= 4: return True
    return False

def analyze_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    color_pages, bw_pages = 0, 0
    color_page_numbers = []
    
    # Rimpicciolisce la risoluzione per non pesare sulla RAM
    mat = fitz.Matrix(0.2, 0.2) 

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Se trova subito testo o immagini a colori, salta la scansione dei pixel
        if has_color_text(page) or has_color_images(page, doc):
            color_pages += 1
            color_page_numbers.append(page_num + 1)
            continue
            
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        if is_grayscale(img): bw_pages += 1
        else:
            color_pages += 1
            color_page_numbers.append(page_num + 1)

    costo_color = color_pages * 0.35
    costo_bw = bw_pages * 0.08
    
    return {
        "pagine_colore": color_pages, "dettaglio_colore": color_page_numbers,
        "pagine_bn": bw_pages, "totale_pagine": len(doc),
        "totale_euro": round(costo_color + costo_bw, 2)
    }

app = Flask(__name__)
CORS(app)

@app.route('/calcola', methods=['POST'])
def calcola():
    if 'file' not in request.files: return jsonify({"errore": "Nessun file caricato"}), 400
    file = request.files['file']
    temp_path = f"temp_{file.filename}"
    file.save(temp_path)
    try: risultato = analyze_pdf(temp_path)
    except Exception as e: return jsonify({"errore": str(e)}), 500
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)
    return jsonify(risultato)

if __name__ == '__main__': app.run(port=5000)
