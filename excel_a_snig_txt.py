from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


SNIG_PATTERN = re.compile(r"(?<!\d)(8580000\d{8})(?!\d)")
FIXED_PREFIX = "A0000000"
FIXED_SUFFIX = "|.|.|.|.|.|.|.|.|.|.|]"


def extraer_caravanas_desde_excel(ruta_excel: Path) -> list[str]:
    try:
        hojas = pd.read_excel(
            ruta_excel,
            sheet_name=None,
            header=None,
            dtype=str,
            engine="openpyxl",
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"No se encontró el archivo Excel: {ruta_excel}") from exc
    except ValueError as exc:
        raise ValueError(f"No se pudo leer el Excel (formato inválido o vacío): {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error leyendo el Excel: {exc}") from exc

    if not hojas:
        raise ValueError("El Excel no contiene hojas para procesar.")

    caravanas: list[str] = []
    vistas: set[str] = set()

    for _, df in hojas.items():
        if df is None or df.empty:
            continue

        for fila in df.itertuples(index=False, name=None):
            for celda in fila:
                if celda is None:
                    continue
                texto = str(celda)
                for match in SNIG_PATTERN.findall(texto):
                    if match not in vistas:
                        vistas.add(match)
                        caravanas.append(match)

    return caravanas


def construir_lineas_salida(caravanas: list[str], guia: str, ahora: datetime | None = None) -> list[str]:
    if ahora is None:
        ahora = datetime.now()

    fecha = ahora.strftime("%d%m%Y")
    hora = ahora.strftime("%H%M")
    return [
        f"[|{FIXED_PREFIX}{caravana}|{fecha}|{hora}|{guia}{FIXED_SUFFIX}"
        for caravana in caravanas
    ]


def pedir_guia() -> str:
    guia = input("Ingresá el número de guía (ej: D674195): ").strip()
    if not guia:
        raise ValueError("El número de guía no puede estar vacío.")
    return guia


def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convierte caravanas SNIG encontradas en Excel a TXT con formato específico."
    )
    parser.add_argument(
        "excel",
        type=Path,
        help="Ruta al archivo Excel de entrada (.xlsx).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "salida_snig.txt",
        help="Ruta del TXT de salida (default: salida_snig.txt junto al script).",
    )
    return parser.parse_args()


def main() -> int:
    args = parsear_argumentos()
    ruta_excel = args.excel.expanduser().resolve()
    ruta_salida = args.output.expanduser().resolve()

    if ruta_excel.suffix.lower() != ".xlsx":
        print("Error: el archivo de entrada debe ser .xlsx", file=sys.stderr)
        return 1

    if not ruta_excel.exists():
        print(f"Error: no existe el archivo de entrada: {ruta_excel}", file=sys.stderr)
        return 1

    try:
        guia = pedir_guia()
        caravanas = extraer_caravanas_desde_excel(ruta_excel)

        if not caravanas:
            print(
                "No se encontraron caravanas SNIG válidas (15 dígitos con prefijo 8580000).",
                file=sys.stderr,
            )
            return 2

        lineas = construir_lineas_salida(caravanas, guia)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        ruta_salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")

        print(f"OK: se generó {ruta_salida}")
        print(f"Total de caravanas únicas exportadas: {len(caravanas)}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
