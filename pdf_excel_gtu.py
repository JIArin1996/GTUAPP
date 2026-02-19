import tempfile
from pathlib import Path

from flask import Flask, render_template, request
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


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nombre_archivo = sanitizar_nombre_archivo(request.form.get("nombre_archivo", ""))
        archivo_pdf = request.files.get("archivo_pdf")

        if not nombre_archivo:
            return render_template("index.html", error="Ingresá un nombre de archivo válido.")

        if not archivo_pdf or not archivo_pdf.filename.lower().endswith(".pdf"):
            return render_template("index.html", error="Debes cargar un archivo PDF válido.")

        try:
            temp_dir = Path(tempfile.gettempdir())
            ruta_pdf = temp_dir / "pdf_temporal_gtu.pdf"
            archivo_pdf.save(ruta_pdf)

            texto_entrada = leer_pdf(ruta_pdf)
            datos_procesados = procesar_entrada(texto_entrada)

            if not datos_procesados:
                return render_template(
                    "index.html",
                    error="No se encontraron datos con el formato esperado en el PDF.",
                )

            carpeta_descargas = Path.home() / "Downloads"
            carpeta_descargas.mkdir(parents=True, exist_ok=True)
            ruta_excel = carpeta_descargas / f"{nombre_archivo}.xlsx"

            generar_excel(datos_procesados, ruta_excel)
            return render_template("success.html", ruta_excel=str(ruta_excel))
        except Exception as exc:
            return render_template(
                "index.html",
                error=f"Ocurrió un error al procesar el archivo: {exc}",
            )

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=False)
