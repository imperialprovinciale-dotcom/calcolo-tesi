import fitz  # PyMuPDF
from PIL import Image, ImageChops
import io
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

# ------------------------------------------------------------------
# STESSO MODELLO DEL PROGRAMMA DELLA STAMPANTE (analizzatore_gui.py)
# Una pagina e' a COLORI solo se, renderizzata a 72 dpi (come in
# negozio), contiene almeno un pixel con R, G, B diversi.
# Testo colorato e immagini CMYK/trasparenti NON fanno piu' scattare
# il colore da sole: conta solo come appare la pagina.
# ------------------------------------------------------------------

def is_grayscale(image):
    if image.mode not in ("L", "RGB"):
        return False
    if image.mode == "L":
        return True
    r, g, b = image.convert("RGB").split()
    # identico al controllo pixel per pixel della stampante, ma veloce
    return ImageChops.difference(r, g).getextrema()[1] == 0 and \
           ImageChops.difference(g, b).getextrema()[1] == 0

def analyze_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    try:
        color_pages, bw_pages = 0, 0
        color_page_numbers = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()  # risoluzione standard (72 dpi), come la stampante
            # stessi pixel del PNG della stampante, ma senza comprimere/decomprimere (piu' leggero)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if is_grayscale(img):
                bw_pages += 1
            else:
                color_pages += 1
                color_page_numbers.append(page_num + 1)
            pix = None
            img.close()
        totale = len(doc)
    finally:
        doc.close()

    costo_color = color_pages * 0.35
    costo_bw = bw_pages * 0.08
    return {
        "pagine_colore": color_pages, "dettaglio_colore": color_page_numbers,
        "pagine_bn": bw_pages, "totale_pagine": totale,
        "totale_euro": round(costo_color + costo_bw, 2)
    }

app = Flask(__name__)
CORS(app)

@app.route('/calcola', methods=['POST'])
def calcola():
    if 'file' not in request.files: return jsonify({"errore": "Nessun file caricato"}), 400
    file = request.files['file']
    temp_path = f"temp_{os.getpid()}_{os.path.basename(file.filename or 'tesi.pdf')}"
    file.save(temp_path)
    try: risultato = analyze_pdf(temp_path)
    except Exception as e: return jsonify({"errore": str(e)}), 500
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)
    return jsonify(risultato)

if __name__ == '__main__': app.run(port=5000)
