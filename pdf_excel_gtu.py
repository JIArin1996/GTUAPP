import re
import pandas as pd
from flask import Flask, request, render_template, send_file
from PyPDF2 import PdfReader
import tempfile
import os
from pathlib import Path

app = Flask(__name__)

def leer_pdf(ruta_pdf):
    with open(ruta_pdf, "rb") as archivo:
        lector = PdfReader(archivo)
        texto = "\n".join([pagina.extract_text() or "" for pagina in lector.pages])
    return texto.strip()

def procesar_entrada(texto):
    # Expresión regular para capturar los datos, permitiendo 'H' o 'M' y valores 'S/E' o 'S/S'
    patron = re.compile(r"\)\s*(\d+)\s+(H|M|S/S)\s+(\d+|S/E)")

    # Extraer datos usando regex
    datos = patron.findall(texto)

    # Ordenar los datos por código numérico manteniendo el orden original de apariciones repetidas
    datos_ordenados = sorted(datos, key=lambda x: (int(x[0]) if x[0].isdigit() else float('inf'), datos.index(x)))

    return datos_ordenados

def generar_excel(datos, nombre_archivo):
    # Crear un DataFrame con los datos procesados
    df = pd.DataFrame(datos, columns=["Caravana", "Sexo", "Edad"])

    # Guardar en un archivo Excel
    df.to_excel(nombre_archivo, index=False)
    return nombre_archivo

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nombre_archivo = request.form['nombre_archivo']

        # Guardar PDF en carpeta temporal
        temp_dir = tempfile.gettempdir()
        ruta_pdf = os.path.join(temp_dir, "pdf_temporal.pdf")
        archivo_pdf = request.files['archivo_pdf']
        archivo_pdf.save(ruta_pdf)

        # Procesar datos
        texto_entrada = leer_pdf(ruta_pdf)
        datos_procesados = procesar_entrada(texto_entrada)

        # Guardar Excel directamente en la carpeta Descargas del usuario
        carpeta_descargas = str(Path.home() / "Downloads")
        ruta_excel = os.path.join(carpeta_descargas, f"{nombre_archivo}.xlsx")

        generar_excel(datos_procesados, ruta_excel)

        return render_template('success.html', ruta_excel=ruta_excel)


    return render_template('index.html')