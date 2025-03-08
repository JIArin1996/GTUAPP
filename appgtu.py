import re
import pandas as pd
import tempfile
import os
from flask import Flask, request, render_template_string, send_file, after_this_request
from PyPDF2 import PdfReader

app = Flask(__name__)

def leer_pdf(ruta_pdf):
    with open(ruta_pdf, "rb") as archivo:
        lector = PdfReader(archivo)
        texto = "\n".join([pagina.extract_text() or "" for pagina in lector.pages])
    return texto.strip()

def procesar_entrada(texto):
    # Expresión regular para capturar los datos, permitiendo 'H' o 'M' y valores 'S/E' o 'S/S'
    patron = re.compile(r"\)\s*(\d+)\s+(H|M|S/S)\s+(\d+|S/E)")
    datos = patron.findall(texto)
    datos_ordenados = sorted(datos, key=lambda x: (int(x[0]) if x[0].isdigit() else float('inf'), datos.index(x)))
    return datos_ordenados

def generar_excel(datos):
    # Crear archivo temporal
    temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    nombre_excel = temp_excel.name
    temp_excel.close()  # Cerrar para que openpyxl no bloquee el archivo

    # Guardar en Excel y cerrarlo correctamente
    df = pd.DataFrame(datos, columns=["Caravana", "Sexo", "Edad"])
    with pd.ExcelWriter(nombre_excel, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    return nombre_excel

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nombre_archivo = request.form['nombre_archivo']
        archivo_pdf = request.files['archivo_pdf']

        # Guardar PDF en un archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            archivo_pdf.save(temp_pdf.name)
            temp_pdf_path = temp_pdf.name  

        try:
            # Leer y procesar PDF
            texto_entrada = leer_pdf(temp_pdf_path)
            datos_procesados = procesar_entrada(texto_entrada)

            # Generar Excel en archivo temporal
            archivo_excel = generar_excel(datos_procesados)

            # Marcar el archivo para eliminación después de la respuesta
            @after_this_request
            def limpiar_archivos(response):
                try:
                    os.remove(temp_pdf_path)
                    os.remove(archivo_excel)
                except Exception as e:
                    print(f"Error al eliminar archivos temporales: {e}")
                return response

            return send_file(archivo_excel, as_attachment=True, download_name=f"{nombre_archivo}.xlsx")

        except Exception as e:
            return f"Error: {e}"

    return render_template_string('''
<!doctype html>
<html>
<head>
    <link rel="stylesheet" type="text/css" href="{{ url_for('static', filename='style.css') }}">
    <title>Generar Excel</title>
</head>
<body>
    <div class="container">
        <div class="form-container">
            <h2>Ingrese el nombre del archivo y cargue el PDF</h2>
            <form method="post" enctype="multipart/form-data">
                <label>Nombre del archivo (sin extensión):</label>
                <input type="text" name="nombre_archivo" required><br><br>
                <label>Cargar PDF:</label><br>
                <input type="file" name="archivo_pdf" accept="application/pdf" required><br><br>
                <input type="submit" value="Generar Excel">
            </form>
        </div>
        <div class="img-container">
            <img src="{{ url_for('static', filename='logo.png') }}" alt="Logo de la empresa">
        </div>
    </div>
</body>
</html>
    ''')

if __name__ == "__main__":
    app.run(debug=True)