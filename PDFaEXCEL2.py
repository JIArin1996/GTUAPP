import re
import pandas as pd
from flask import Flask, request, render_template_string, send_file
from PyPDF2 import PdfReader
import os

tmp_pdf_dir = "tmp_pdfs"
tmp_excel_file = "xls_temporal.xlsx"
app = Flask(__name__)

# Asegurar la existencia del directorio temporal
os.makedirs(tmp_pdf_dir, exist_ok=True)

def leer_pdf(ruta_pdf):
    with open(ruta_pdf, "rb") as archivo:
        lector = PdfReader(archivo)
        texto = "\n".join([pagina.extract_text() or "" for pagina in lector.pages])
    return texto.strip()

def procesar_entrada(texto):
    patron = re.compile(r"\)\s*(\d+)\s+(H|M|S/S)\s+(\d+|S/E)")
    datos = patron.findall(texto)
    datos_ordenados = sorted(datos, key=lambda x: (int(x[0]) if x[0].isdigit() else float('inf'), datos.index(x)))
    return datos_ordenados

def generar_excel(datos, nombre_archivo):
    df = pd.DataFrame(datos, columns=["Caravana", "Sexo", "Edad"])
    df.to_excel(nombre_archivo, index=False)
    return nombre_archivo

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nombre_archivo = request.form['nombre_archivo']
        archivos_pdf = request.files.getlist('archivos_pdf')
        
        datos_totales = []
        
        for archivo_pdf in archivos_pdf:
            ruta_pdf = os.path.join(tmp_pdf_dir, archivo_pdf.filename)
            archivo_pdf.save(ruta_pdf)
            texto_entrada = leer_pdf(ruta_pdf)
            datos_totales.extend(procesar_entrada(texto_entrada))
        
        archivo_generado = generar_excel(datos_totales, tmp_excel_file)
        
        return send_file(archivo_generado, as_attachment=True, download_name=f"{nombre_archivo}.xlsx")
    
    return render_template_string('''
    <!doctype html>
    <html>
    <head>
        <title>Generar Excel</title>
    </head>
    <body>
        <h2>Ingrese el nombre del archivo y cargue los PDFs</h2>
        <form method="post" enctype="multipart/form-data">
            <label>Nombre del archivo (sin extensión):</label>
            <input type="text" name="nombre_archivo" required><br><br>
            <label>Cargar PDFs:</label><br>
            <input type="file" name="archivos_pdf" accept="application/pdf" multiple required><br><br>
            <input type="submit" value="Generar Excel">
        </form>
    </body>
    </html>
    ''')

if __name__ == "__main__":
    app.run(debug=True)
