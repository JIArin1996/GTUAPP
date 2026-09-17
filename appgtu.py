import os
import re
import subprocess
import tempfile
from num2words import num2words
from datetime import datetime
from pathlib import Path
import pandas as pd
import typst
from flask import Flask, after_this_request, jsonify, render_template, request, send_file
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from parser_utils import procesar_entrada, sanitizar_nombre_archivo
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ENV = os.getenv("FLASK_ENV", "production").lower()
IS_DEV = ENV == "development"

app.config["TEMPLATES_AUTO_RELOAD"] = IS_DEV
app.config["DEBUG"] = IS_DEV


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


def extraer_caravanas_txt(archivos_txt) -> list[tuple[str, str]]:
    resultados = []
    # Usamos ^.*? para tolerar cualquier caracter invisible/BOM al comienzo de la linea
    pattern = re.compile(r"^.*?\[\|A0000000(8580000\d{8})")
    for archivo in archivos_txt:
        if not archivo or not archivo.filename:
            continue
        # utf-8-sig remueve la firma BOM automáticamente
        lineas = archivo.read().decode("utf-8-sig", errors="ignore").splitlines()
        filename = archivo.filename
        for linea in lineas:
            linea = linea.strip()
            match = pattern.search(linea)
            if match:
                caravana = match.group(1)
                resultados.append((caravana, filename))
    return resultados


def unir_pdfs(rutas_pdf, ruta_salida: Path) -> Path:
    escritor = PdfWriter()
    for ruta_pdf in rutas_pdf:
        lector = PdfReader(str(ruta_pdf))
        for pagina in lector.pages:
            escritor.add_page(pagina)
    with ruta_salida.open("wb") as archivo_salida:
        escritor.write(archivo_salida)
    return ruta_salida


def unir_imagenes_a_pdf(rutas_imagenes, ruta_salida: Path) -> Path:
    imagenes = [Image.open(ruta).convert("RGB") for ruta in rutas_imagenes]
    primera, resto = imagenes[0], imagenes[1:]
    primera.save(ruta_salida, save_all=True, append_images=resto)
    return ruta_salida


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


def numero_a_letras(valor: str) -> str:
    """Convierte un string numérico a texto en mayúsculas (ej: '100' -> 'CIEN')."""
    try:
        val = int(valor)
        if val == 0:
            return ""
        return num2words(val, lang='es').upper()
    except (ValueError, TypeError):
        return ""
    

def generar_pdf_oficio_typst(
    tipo_operacion: str = "",
    cambio_propiedad: str = "con",
    # DICOSE
    dicose_a: str = "", razon_social_a: str = "", domicilio_a: str = "",
    dicose_b: str = "", razon_social_b: str = "", domicilio_b: str = "",
    dicose_c: str = "", razon_social_c: str = "", domicilio_c: str = "",
    dicose_d: str = "", razon_social_d: str = "", domicilio_d: str = "",
    # VACUNOS
    vac_toros: str = "", vac_vacas: str = "", vac_nov_3: str = "",
    vac_nov_2_3: str = "", vac_nov_1_2: str = "", vac_vaq_2: str = "",
    vac_vaq_1_2: str = "", vac_terneros: str = "", vac_total: str = "",
    # OVINOS
    ovi_carneros: str = "", ovi_ovejas: str = "", ovi_capones: str = "",
    ovi_borregas: str = "", ovi_corderas_dl: str = "", ovi_corderos_dl: str = "",
    ovi_mamones: str = "", ovi_total: str = "",
    # FECHA, CI Y RUT
    fecha_dia: str = "",
    fecha_mes: str = "",
    fecha_anio: str = "",
    ci_firma: str = "",
    rut_vendedor: str = "",
    ruta_salida: Path = None
) -> Path:
    pos_y_guion = "4.25cm" if cambio_propiedad == "con" else "4.80cm"

    vac_total_letras = numero_a_letras(vac_total)
    ovi_total_letras = numero_a_letras(ovi_total)

    # Conversión y formateo previo de datos
    dia_fmt = f"{int(fecha_dia):02d}" if fecha_dia.isdigit() else ""
    mes_fmt = f"{int(fecha_mes):02d}" if fecha_mes.isdigit() else ""
    anio_fmt = str(fecha_anio)[-2:].zfill(2) if fecha_anio else ""
    ci_fmt = ci_firma.zfill(8)[-8:] if ci_firma else ""
    rut_fmt = rut_vendedor.rjust(13, " ")[-13:] if rut_vendedor else ""

    plantilla_typst = f"""
    #set page(width: 21.6cm, height: 35.5cm, margin: 0cm)
    #set text(font: "Liberation Serif")

    #let formatear-id(cadena) = {{
      let caracteres = cadena.clusters()
      stack(
        dir: ltr,
        spacing: 1mm,
        ..caracteres.map(char => box(
          width: 6mm,
          height: 8mm,
          align(center + horizon, text(size: 8mm, top-edge: "bounds", bottom-edge: "bounds")[#char])
        ))
      )
    }}

    #let texto-casilla(contenido, ancho-max) = {{
      if contenido == "" {{ return }}
      layout(size => {{
        let txt = text(size: 10pt, top-edge: "bounds", bottom-edge: "baseline")[#contenido]
        let tam = measure(txt)
        if tam.width > ancho-max {{
          let factor = (ancho-max / tam.width) * 100%
          box(
            width: ancho-max,
            height: 0pt,
            baseline: 0pt,
            align(center, scale(x: factor, reflow: true)[#txt])
          )
        }} else {{
          box(
            width: ancho-max,
            height: 0pt,
            baseline: 0pt,
            align(center)[#txt]
          )
        }}
      }})
    }}

    #let formatear-cantidad(cadena) = {{
      let chars = str(cadena).clusters()
      while chars.len() < 5 {{
        chars.insert(0, "")
      }}
      let chars-5 = chars.slice(chars.len() - 5)
      stack(
        dir: ltr,
        spacing: 1mm,
        ..chars-5.map(char => box(
          width: 4mm,
          height: 6mm,
          align(center + horizon, text(size: 12pt, top-edge: "bounds", bottom-edge: "bounds")[#char])
        ))
      )
    }}

    // Formateador para casillas fijas de N caracteres (4mm x 6mm, sep 1mm)
    #let formatear-fijo(cadena, largo) = {{
      let chars = str(cadena).clusters()
      while chars.len() < largo {{
        chars.insert(0, "")
      }}
      let chars-final = chars.slice(chars.len() - largo)
      stack(
        dir: ltr,
        spacing: 1mm,
        ..chars-final.map(char => box(
          width: 4mm,
          height: 6mm,
          align(center + horizon, text(size: 12pt, top-edge: "bounds", bottom-edge: "bounds")[#char])
        ))
      )
    }}

    // Formateador para Cédula (8 dígitos, último dígito separado por 2mm)
    #let formatear-ci(cadena) = {{
      let chars = str(cadena).clusters()
      while chars.len() < 8 {{
        chars.insert(0, "")
      }}
      let c = chars.slice(chars.len() - 8)
      let primeros = c.slice(0, 7)
      let ultimo = c.at(7)

      stack(
        dir: ltr,
        spacing: 2mm,
        stack(
          dir: ltr,
          spacing: 1mm,
          ..primeros.map(char => box(
            width: 4mm,
            height: 6mm,
            align(center + horizon, text(size: 12pt, top-edge: "bounds", bottom-edge: "bounds")[#char])
          ))
        ),
        box(
          width: 4mm,
          height: 6mm,
          align(center + horizon, text(size: 12pt, top-edge: "bounds", bottom-edge: "bounds")[#ultimo])
        )
      )
    }}

    // TIPO DE OPERACIÓN
    #place(dx: 9.5cm, dy: 3.2cm)[
      #box(
        height: 0pt,
        baseline: 0pt,
        text(size: 12pt, top-edge: "bounds", bottom-edge: "baseline")[{tipo_operacion}]
      )
    ]

    // Guion "Con / Sin cambio de propiedad"
    #place(dx: 6.3cm, dy: {pos_y_guion})[
      #rect(width: 5mm, height: 2mm, fill: black, outset: 0pt)
    ]

    // DICOSE A, B, C, D
    #place(dx: 3.1cm, dy: 7.15cm)[#formatear-id("{dicose_a}")]
    #place(dx: 3.2cm, dy: 8.5cm)[#texto-casilla("{razon_social_a}", 6.6cm)]
    #place(dx: 4.1cm, dy: 9.05cm)[#texto-casilla("{domicilio_a}", 5.7cm)]

    #place(dx: 13.1cm, dy: 7.15cm)[#formatear-id("{dicose_b}")]
    #place(dx: 13.25cm, dy: 8.5cm)[#texto-casilla("{razon_social_b}", 6.65cm)]
    #place(dx: 14.2cm, dy: 9.05cm)[#texto-casilla("{domicilio_b}", 5.7cm)]

    #place(dx: 3.1cm, dy: 10.6cm)[#formatear-id("{dicose_c}")]
    #place(dx: 3.2cm, dy: 11.8cm)[#texto-casilla("{razon_social_c}", 6.6cm)]
    #place(dx: 4.1cm, dy: 12.5cm)[#texto-casilla("{domicilio_c}", 5.7cm)]

    #place(dx: 13.1cm, dy: 10.6cm)[#formatear-id("{dicose_d}")]
    #place(dx: 13.25cm, dy: 11.8cm)[#texto-casilla("{razon_social_d}", 6.65cm)]
    #place(dx: 14.2cm, dy: 12.5cm)[#texto-casilla("{domicilio_d}", 5.7cm)]

    // COLUMNA VACUNOS
    #place(dx: 4.0cm, dy: 14.20cm)[#formatear-cantidad("{vac_toros}")]
    #place(dx: 4.0cm, dy: 15.05cm)[#formatear-cantidad("{vac_vacas}")]
    #place(dx: 4.0cm, dy: 15.80cm)[#formatear-cantidad("{vac_nov_3}")]
    #place(dx: 4.0cm, dy: 16.65cm)[#formatear-cantidad("{vac_nov_2_3}")]
    #place(dx: 4.0cm, dy: 17.50cm)[#formatear-cantidad("{vac_nov_1_2}")]
    #place(dx: 4.0cm, dy: 18.30cm)[#formatear-cantidad("{vac_vaq_2}")]
    #place(dx: 4.0cm, dy: 19.10cm)[#formatear-cantidad("{vac_vaq_1_2}")]
    #place(dx: 4.0cm, dy: 19.90cm)[#formatear-cantidad("{vac_terneros}")]
    #place(dx: 4.0cm, dy: 20.70cm)[#formatear-cantidad("{vac_total}")]

    // COLUMNA OVINOS
    #place(dx: 9.0cm, dy: 14.20cm)[#formatear-cantidad("{ovi_carneros}")]
    #place(dx: 9.0cm, dy: 15.05cm)[#formatear-cantidad("{ovi_ovejas}")]
    #place(dx: 9.0cm, dy: 15.80cm)[#formatear-cantidad("{ovi_capones}")]
    #place(dx: 9.0cm, dy: 16.65cm)[#formatear-cantidad("{ovi_borregas}")]
    #place(dx: 9.0cm, dy: 17.50cm)[#formatear-cantidad("{ovi_corderas_dl}")]
    #place(dx: 9.0cm, dy: 18.30cm)[#formatear-cantidad("{ovi_corderos_dl}")]
    #place(dx: 9.0cm, dy: 19.10cm)[#formatear-cantidad("{ovi_mamones}")]
    #place(dx: 9.0cm, dy: 19.90cm)[#formatear-cantidad("{ovi_total}")]

    // TOTALES EN LETRAS
    #place(dx: 4.75cm, dy: 21.9cm)[#texto-casilla("{vac_total_letras}", 7.25cm)]
    #place(dx: 15.4cm, dy: 21.9cm)[#texto-casilla("{ovi_total_letras}", 5.0cm)]

    // FECHA (35.5cm - 5.25cm = 30.25cm)
    #place(dx: 7.25cm, dy: 30.35cm)[#formatear-fijo("{dia_fmt}", 2)]
    #place(dx: 9.05cm, dy: 30.35cm)[#formatear-fijo("{mes_fmt}", 2)]
    #place(dx: 10.85cm, dy: 30.35cm)[#formatear-fijo("{anio_fmt}", 2)]

    // CÉDULA FIRMA (35.5cm - 5.40cm = 30.10cm)
    #place(dx: 16.55cm, dy: 30.2cm)[#formatear-ci("{ci_fmt}")]

    // RUT VENDEDOR (35.5cm - 3.15cm = 32.35cm)
    #place(dx: 5.30cm, dy: 31.9cm)[#formatear-fijo("{rut_fmt}", 13)]
    """

    tmp_typ = tempfile.NamedTemporaryFile(prefix="gtu_oficio_", suffix=".typ", delete=False, mode="w", encoding="utf-8")
    ruta_typ = Path(tmp_typ.name)
    tmp_typ.write(plantilla_typst)
    tmp_typ.close()

    try:
        typst.compile(str(ruta_typ), output=str(ruta_salida))
        return ruta_salida
    except RuntimeError as err:
        raise RuntimeError(f"Error al compilar el PDF con Typst: {err}")
    except Exception as err:
        raise RuntimeError(f"Error inesperado durante la compilación: {err}")
    finally:
        if ruta_typ.exists():
            ruta_typ.unlink()


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

    if not re.fullmatch(r"[A-Za-z]\d{6}", guia):
        return respuesta_error("El número de guía debe tener 1 letra seguida de 6 números (ej: D674195).")

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


@app.route("/txt-a-excel", methods=["POST"])
def txt_a_excel():
    archivos_txt = request.files.getlist("archivo_txt")
    nombre_archivo = sanitizar_nombre_archivo(request.form.get("nombre_excel", ""))

    if not nombre_archivo:
        nombre_archivo = "caravanas_extraidas"

    archivos_validos = [archivo for archivo in archivos_txt if archivo and archivo.filename]
    if not archivos_validos:
        return respuesta_error("Debes cargar al menos un archivo TXT.")

    if any(not archivo.filename.lower().endswith(".txt") for archivo in archivos_validos):
        return respuesta_error("Todos los archivos cargados deben ser TXT.")

    try:
        datos_extraidos = extraer_caravanas_txt(archivos_validos)

        if not datos_extraidos:
            return respuesta_error("No se encontraron caravanas válidas en los archivos TXT.")

        tmp_excel = tempfile.NamedTemporaryFile(prefix="gtu_txt_", suffix=".xlsx", delete=False)
        ruta_excel = Path(tmp_excel.name)
        tmp_excel.close()

        df = pd.DataFrame(datos_extraidos, columns=["Caravana", "Archivo Origen"])
        df.to_excel(ruta_excel, index=False)

        @after_this_request
        def cleanup_temporales_txt_excel(response):
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
        return respuesta_error(f"Ocurrió un error al procesar los TXT: {exc}", status_code=500)


@app.route("/unir-pdf", methods=["POST"])
def unir_pdf():
    archivos_pdf = request.files.getlist("archivo_pdf_merge")
    nombre_archivo = sanitizar_nombre_archivo(request.form.get("nombre_pdf_merge", "")) or "pdf_unido"

    archivos_validos = [archivo for archivo in archivos_pdf if archivo and archivo.filename]
    if not archivos_validos:
        return respuesta_error("Debes cargar al menos un archivo PDF.")

    if any(not archivo.filename.lower().endswith(".pdf") for archivo in archivos_validos):
        return respuesta_error("Todos los archivos cargados deben ser PDF.")

    try:
        temp_dir = Path(tempfile.gettempdir())
        rutas_pdf = []
        for idx, archivo in enumerate(archivos_validos):
            ruta_pdf = temp_dir / f"pdf_unir_gtu_{idx}.pdf"
            archivo.save(ruta_pdf)
            rutas_pdf.append(ruta_pdf)

        tmp_salida = tempfile.NamedTemporaryFile(prefix="gtu_pdf_unido_", suffix=".pdf", delete=False)
        ruta_salida = Path(tmp_salida.name)
        tmp_salida.close()

        unir_pdfs(rutas_pdf, ruta_salida)

        @after_this_request
        def cleanup_temporales_unir_pdf(response):
            for ruta_pdf in rutas_pdf:
                try:
                    if ruta_pdf.exists():
                        ruta_pdf.unlink()
                except OSError:
                    pass

            try:
                if ruta_salida.exists():
                    ruta_salida.unlink()
            except OSError:
                pass

            return response

        return send_file(
            ruta_salida,
            as_attachment=True,
            download_name=f"{nombre_archivo}.pdf",
            mimetype="application/pdf",
        )
    except Exception as exc:
        return respuesta_error(f"Ocurrió un error al unir los PDF: {exc}", status_code=500)


@app.route("/unir-imagenes", methods=["POST"])
def unir_imagenes():
    archivos_imagenes = request.files.getlist("archivo_imagen_merge")
    nombre_archivo = sanitizar_nombre_archivo(request.form.get("nombre_imagen_merge", "")) or "imagenes_unidas"

    archivos_validos = [archivo for archivo in archivos_imagenes if archivo and archivo.filename]
    if not archivos_validos:
        return respuesta_error("Debes cargar al menos una imagen.")

    extensiones_validas = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    if any(not archivo.filename.lower().endswith(extensiones_validas) for archivo in archivos_validos):
        return respuesta_error("Todos los archivos cargados deben ser imágenes (PNG, JPG, JPEG, WEBP o BMP).")

    try:
        temp_dir = Path(tempfile.gettempdir())
        rutas_imagenes = []
        for idx, archivo in enumerate(archivos_validos):
            extension = Path(archivo.filename).suffix.lower()
            ruta_imagen = temp_dir / f"img_unir_gtu_{idx}{extension}"
            archivo.save(ruta_imagen)
            rutas_imagenes.append(ruta_imagen)

        tmp_salida = tempfile.NamedTemporaryFile(prefix="gtu_img_unidas_", suffix=".pdf", delete=False)
        ruta_salida = Path(tmp_salida.name)
        tmp_salida.close()

        unir_imagenes_a_pdf(rutas_imagenes, ruta_salida)

        @after_this_request
        def cleanup_temporales_unir_imagenes(response):
            for ruta_imagen in rutas_imagenes:
                try:
                    if ruta_imagen.exists():
                        ruta_imagen.unlink()
                except OSError:
                    pass

            try:
                if ruta_salida.exists():
                    ruta_salida.unlink()
            except OSError:
                pass

            return response

        return send_file(
            ruta_salida,
            as_attachment=True,
            download_name=f"{nombre_archivo}.pdf",
            mimetype="application/pdf",
        )
    except Exception as exc:
        return respuesta_error(f"Ocurrió un error al unir las imágenes: {exc}", status_code=500)


@app.route("/generar-oficio", methods=["POST"])
def generar_oficio():
    tipo_operacion = request.form.get("tipo_operacion", "").strip()
    cambio_propiedad = request.form.get("cambio_propiedad", "con")

    # Bloques DICOSE
    dicose_a = request.form.get("dicose_a", "").strip()
    razon_social_a = request.form.get("razon_social_a", "").strip()
    domicilio_a = request.form.get("domicilio_a", "").strip()

    dicose_b = request.form.get("dicose_b", "").strip()
    razon_social_b = request.form.get("razon_social_b", "").strip()
    domicilio_b = request.form.get("domicilio_b", "").strip()

    dicose_c = request.form.get("dicose_c", "").strip()
    razon_social_c = request.form.get("razon_social_c", "").strip()
    domicilio_c = request.form.get("domicilio_c", "").strip()

    dicose_d = request.form.get("dicose_d", "").strip()
    razon_social_d = request.form.get("razon_social_d", "").strip()
    domicilio_d = request.form.get("domicilio_d", "").strip()

    # Vacunos
    vac_toros = request.form.get("vac_toros", "").strip()
    vac_vacas = request.form.get("vac_vacas", "").strip()
    vac_nov_3 = request.form.get("vac_nov_3", "").strip()
    vac_nov_2_3 = request.form.get("vac_nov_2_3", "").strip()
    vac_nov_1_2 = request.form.get("vac_nov_1_2", "").strip()
    vac_vaq_2 = request.form.get("vac_vaq_2", "").strip()
    vac_vaq_1_2 = request.form.get("vac_vaq_1_2", "").strip()
    vac_terneros = request.form.get("vac_terneros", "").strip()
    vac_total = request.form.get("vac_total", "").strip()

    # Ovinos
    ovi_carneros = request.form.get("ovi_carneros", "").strip()
    ovi_ovejas = request.form.get("ovi_ovejas", "").strip()
    ovi_capones = request.form.get("ovi_capones", "").strip()
    ovi_borregas = request.form.get("ovi_borregas", "").strip()
    ovi_corderas_dl = request.form.get("ovi_corderas_dl", "").strip()
    ovi_corderos_dl = request.form.get("ovi_corderos_dl", "").strip()
    ovi_mamones = request.form.get("ovi_mamones", "").strip()
    ovi_total = request.form.get("ovi_total", "").strip()

    # Nuevos Campos
    fecha_dia = request.form.get("fecha_dia", "").strip()
    fecha_mes = request.form.get("fecha_mes", "").strip()
    fecha_anio = request.form.get("fecha_anio", "").strip()
    ci_firma = request.form.get("ci_firma", "").strip()
    rut_vendedor = request.form.get("rut_vendedor", "").strip()

    nombre_archivo = sanitizar_nombre_archivo(request.form.get("nombre_oficio", "")) or "oficio_prueba"

    try:
        tmp_pdf = tempfile.NamedTemporaryFile(prefix="gtu_oficio_out_", suffix=".pdf", delete=False)
        ruta_salida = Path(tmp_pdf.name)
        tmp_pdf.close()

        generar_pdf_oficio_typst(
            tipo_operacion=tipo_operacion,
            cambio_propiedad=cambio_propiedad,
            dicose_a=dicose_a, razon_social_a=razon_social_a, domicilio_a=domicilio_a,
            dicose_b=dicose_b, razon_social_b=razon_social_b, domicilio_b=domicilio_b,
            dicose_c=dicose_c, razon_social_c=razon_social_c, domicilio_c=domicilio_c,
            dicose_d=dicose_d, razon_social_d=razon_social_d, domicilio_d=domicilio_d,
            vac_toros=vac_toros, vac_vacas=vac_vacas, vac_nov_3=vac_nov_3,
            vac_nov_2_3=vac_nov_2_3, vac_nov_1_2=vac_nov_1_2, vac_vaq_2=vac_vaq_2,
            vac_vaq_1_2=vac_vaq_1_2, vac_terneros=vac_terneros, vac_total=vac_total,
            ovi_carneros=ovi_carneros, ovi_ovejas=ovi_ovejas, ovi_capones=ovi_capones,
            ovi_borregas=ovi_borregas, ovi_corderas_dl=ovi_corderas_dl,
            ovi_corderos_dl=ovi_corderos_dl, ovi_mamones=ovi_mamones, ovi_total=ovi_total,
            fecha_dia=fecha_dia, fecha_mes=fecha_mes, fecha_anio=fecha_anio,
            ci_firma=ci_firma, rut_vendedor=rut_vendedor,
            ruta_salida=ruta_salida
        )

        @after_this_request
        def cleanup_temporales_oficio(response):
            try:
                if ruta_salida.exists():
                    ruta_salida.unlink()
            except OSError:
                pass
            return response

        return send_file(
            ruta_salida,
            as_attachment=False,
            download_name=f"{nombre_archivo}.pdf",
            mimetype="application/pdf",
        )
    except Exception as exc:
        return respuesta_error(f"Error al generar el oficio: {exc}", status_code=500)
    
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", 5000)),
        debug=IS_DEV
    )
