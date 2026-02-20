import tempfile
from pathlib import Path

from flask import Flask, after_this_request, jsonify, render_template, request, send_file
from PyPDF2 import PdfReader

from parser_utils import procesar_entrada, sanitizar_nombre_archivo

app = Flask(__name__)

def leer_pdf(ruta_pdf: Path) -> str:
    with ruta_pdf.open("rb") as archivo:
        lector = PdfReader(archivo)
        texto = "\n".join([pagina.extract_text() or "" for pagina in lector.pages])
    return texto.strip()


def generar_excel(datos, ruta_excel: Path) -> Path:
    import pandas as pd

    df = pd.DataFrame(datos, columns=["Caravana", "Sexo", "Edad"])
    df.to_excel(ruta_excel, index=False)
    return ruta_excel


def es_peticion_ajax() -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def respuesta_error(mensaje: str, status_code: int = 400):
    if es_peticion_ajax():
        return jsonify({"ok": False, "error": mensaje}), status_code
    return render_template("index.html", error=mensaje), status_code


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nombre_archivo = sanitizar_nombre_archivo(request.form.get("nombre_archivo", ""))
        archivos_pdf = request.files.getlist("archivo_pdf")

        if not nombre_archivo:
            return respuesta_error("Ingresá un nombre de archivo válido.")

        archivos_validos = [archivo for archivo in archivos_pdf if archivo and archivo.filename]
        if not archivos_validos:
            return respuesta_error("Debes cargar al menos un archivo PDF.")

        if any(not archivo.filename.lower().endswith(".pdf") for archivo in archivos_validos):
            return respuesta_error("Todos los archivos cargados deben ser PDF.")

        try:
            temp_dir = Path(tempfile.gettempdir())
            rutas_pdf = []
            datos_procesados = []

            for idx, archivo_pdf in enumerate(archivos_validos):
                ruta_pdf = temp_dir / f"pdf_temporal_gtu_{idx}.pdf"
                archivo_pdf.save(ruta_pdf)
                rutas_pdf.append(ruta_pdf)

                texto_entrada = leer_pdf(ruta_pdf)
                datos_procesados.extend(procesar_entrada(texto_entrada))

            if not datos_procesados:
                return respuesta_error("No se encontraron datos con el formato esperado en los PDF.")

            tmp_excel = tempfile.NamedTemporaryFile(prefix="gtu_", suffix=".xlsx", delete=False)
            ruta_excel = Path(tmp_excel.name)
            tmp_excel.close()

            generar_excel(datos_procesados, ruta_excel)

            @after_this_request
            def cleanup_temporales(response):
                for ruta_pdf in rutas_pdf:
                    try:
                        if ruta_pdf.exists():
                            ruta_pdf.unlink()
                    except OSError:
                        pass

                try:
                    if ruta_excel.exists():
                        ruta_excel.unlink()
                except OSError:
                    pass

                return response

            return send_file(
                ruta_excel,
                as_attachment=True,
                download_name=f"{nombre_archivo}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as exc:
            return respuesta_error(f"Ocurrió un error al procesar el archivo: {exc}", status_code=500)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=False)
