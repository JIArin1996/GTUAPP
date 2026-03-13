import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from pdf_excel_gtu import construir_txt_snig, extraer_caravanas_snig_excel


class ExcelATxtTests(unittest.TestCase):
    def test_extrae_snig_unicos_en_orden(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            ruta_excel = Path(tmp.name)

        try:
            with pd.ExcelWriter(ruta_excel, engine="openpyxl") as writer:
                pd.DataFrame(
                    [["Caravana: 858000012345678", "x"], ["repetida 858000012345678", "858000076543210"]]
                ).to_excel(writer, index=False, header=False, sheet_name="Hoja1")
                pd.DataFrame([["otro dato", "858000011112222"]]).to_excel(
                    writer, index=False, header=False, sheet_name="Hoja2"
                )

            caravanas = extraer_caravanas_snig_excel(ruta_excel)
            self.assertEqual(caravanas, ["858000012345678", "858000076543210", "858000011112222"])
        finally:
            if ruta_excel.exists():
                ruta_excel.unlink()

    def test_construye_formato_salida(self):
        lineas = construir_txt_snig(
            ["858000012345678"],
            "D674195",
            ahora=datetime(2026, 2, 23, 8, 0),
        )
        self.assertEqual(
            lineas,
            "[|A0000000858000012345678|23022026|0800|D674195|.|.|.|.|.|.|.|.|.|.|]\n",
        )


if __name__ == "__main__":
    unittest.main()
