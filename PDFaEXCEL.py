import re
import pandas as pd
from flask import Flask, request, render_template, send_file
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
        
        # Guardar el archivo PDF que sube el usuario
        archivo_pdf = request.files['archivo_pdf']
        archivo_pdf.save("pdf_temporal")

        texto_entrada = leer_pdf("pdf_temporal")
        datos_procesados = procesar_entrada(texto_entrada)
        archivo_generado = generar_excel(datos_procesados, "xls_temporal.xlsx")

        return send_file(archivo_generado, as_attachment=True, download_name=f"{nombre_archivo}.xlsx")

    return render_template('index.html')

#     return render_template_string('''
# <!doctype html>
# <html>
# <head>
#     <link rel="stylesheet" type="text/css" href="{{ url_for('static', filename='style.css') }}">
#     <title>Generar Excel</title>
# </head>
# <body>
#     <div class="container">
#         <!-- Formulario a la izquierda -->
#         <div class="form-container">
#             <h2>Ingrese el nombre del archivo y cargue el PDF</h2>
#             <form method="post" enctype="multipart/form-data">
#                 <label>Nombre del archivo (sin extensión):</label>
#                 <input type="text" name="nombre_archivo" required><br><br>
#                 <label>Cargar PDF:</label><br>
#                 <input type="file" name="archivo_pdf" accept="application/pdf" required><br><br>
#                 <input type="submit" value="Generar Excel">
#             </form>
#         </div>

#         <!-- Imagen/logo a la derecha (si es necesario) -->
#         <div class="img-container">
#             <!-- Reemplaza 'logo.png' por tu imagen real en la carpeta 'static' -->
#             <img src="{{ url_for('static', filename='logo.png') }}" alt="Logo de la empresa">
#         </div>
#     </div>
# </body>
# </html>

#     ''')

if __name__ == "__main__":
    app.run(debug=True)