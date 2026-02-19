import re

PATRON_DATOS = re.compile(r"\)\s*(\d+)\s+(H|M|S/S)\s+(\d+|S/E)")
NOMBRE_INVALIDO = re.compile(r"[<>:\"/\\|?*\x00-\x1F]")


def procesar_entrada(texto: str):
    datos = PATRON_DATOS.findall(texto)
    datos_ordenados = sorted(
        datos,
        key=lambda x: (
            int(x[0]) if x[0].isdigit() else float("inf"),
            datos.index(x),
        ),
    )
    return datos_ordenados


def sanitizar_nombre_archivo(nombre: str) -> str:
    nombre = (nombre or "").strip().replace(".xlsx", "")
    nombre = NOMBRE_INVALIDO.sub("_", nombre)
    return nombre[:120]
