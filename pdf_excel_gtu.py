import re
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, after_this_request, jsonify, render_template, request, send_file
from PyPDF2 import PdfReader

from parser_utils import procesar_entrada, sanitizar_nombre_archivo

app = Flask(__name__)
SNIG_PATTERN = re.compile(r"(?<!\d)(8580000\d{8})(?!\d)")
TXT_SUFFIX = "|.|.|.|.|.|.|.|.|.|.|]"
TXT_PREFIX = "A0000000"


def leer_pdf(ruta_pdf: Path) -> str:
    with ruta_pdf.open("rb") as archivo:
        lector = PdfReader(archivo)
        texto = "\n".join([pagina.extract_text() or "" for pagina in lector.pages])
    return texto.strip()


def generar_excel(datos, ruta_excel: Path) -> Path:
    df = pd.DataFrame(datos, columns=["Caravana", "Sexo", "Edad"])
    df.to_excel(ruta_excel, index=False)
    return ruta_excel


def es_peticion_ajax() -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def respuesta_error(mensaje: str, status_code: int = 400):
    if es_peticion_ajax():
        return jsonify({"ok": False, "error": mensaje}), status_code
    return render_template("index.html", error=mensaje), status_code


def extraer_caravanas_snig_excel(ruta_excel: Path):
    hojas = pd.read_excel(
        ruta_excel,
        sheet_name=None,
        header=None,
        dtype=str,
        engine="openpyxl",
    )

    caravanas = []
    vistas = set()

    for _, df in hojas.items():
        if df is None or df.empty:
            continue

        for fila in df.itertuples(index=False, name=None):
            for celda in fila:
                if celda is None:
                    continue
                for match in SNIG_PATTERN.findall(str(celda)):
                    if match not in vistas:
                        vistas.add(match)
                        caravanas.append(match)

    return caravanas


def construir_txt_snig(caravanas, guia: str, ahora: datetime | None = None) -> str:
    if ahora is None:
        ahora = datetime.now()
    fecha = ahora.strftime("%d%m%Y")
    hora = ahora.strftime("%H%M")
    lineas = [
        f"[|{TXT_PREFIX}{caravana}|{fecha}|{hora}|{guia}{TXT_SUFFIX}"
        for caravana in caravanas
    ]
    return "\n".join(lineas) + "\n"


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


@app.route("/excel-a-txt", methods=["POST"])
def excel_a_txt():
    archivo_excel = request.files.get("archivo_excel")
    guia = (request.form.get("guia") or "").strip()
    nombre_archivo = sanitizar_nombre_archivo(request.form.get("nombre_txt", ""))

    if not archivo_excel or not archivo_excel.filename:
        return respuesta_error("Debes cargar un archivo Excel (.xlsx).")

    if not archivo_excel.filename.lower().endswith(".xlsx"):
        return respuesta_error("El archivo debe tener extensión .xlsx.")

    if not guia:
        return respuesta_error("Debes ingresar el número de guía.")

    if not nombre_archivo:
        nombre_archivo = "salida_snig"

    ruta_excel = None
    ruta_txt = None

    try:
        tmp_excel = tempfile.NamedTemporaryFile(prefix="excel_temporal_gtu_", suffix=".xlsx", delete=False)
        ruta_excel = Path(tmp_excel.name)
        tmp_excel.close()
        archivo_excel.save(ruta_excel)

        caravanas = extraer_caravanas_snig_excel(ruta_excel)
        if not caravanas:
            return respuesta_error(
                "No se encontraron caravanas SNIG válidas (15 dígitos que comiencen con 8580000)."
            )

        contenido_txt = construir_txt_snig(caravanas, guia)

        tmp_txt = tempfile.NamedTemporaryFile(prefix="gtu_snig_", suffix=".txt", delete=False)
        ruta_txt = Path(tmp_txt.name)
        tmp_txt.close()
        ruta_txt.write_text(contenido_txt, encoding="utf-8")

        @after_this_request
        def cleanup_temporales_excel_txt(response):
            try:
                if ruta_excel and ruta_excel.exists():
                    ruta_excel.unlink()
            except OSError:
                pass

            try:
                if ruta_txt and ruta_txt.exists():
                    ruta_txt.unlink()
            except OSError:
                pass

            return response

        download_name = f"{nombre_archivo.replace('.txt', '')}.txt"
        return send_file(
            ruta_txt,
            as_attachment=True,
            download_name=download_name,
            mimetype="text/plain; charset=utf-8",
        )
    except Exception as exc:
        return respuesta_error(f"Ocurrió un error al procesar el Excel: {exc}", status_code=500)


if __name__ == "__main__":
    app.run(debug=False)
