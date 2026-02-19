import unittest

from parser_utils import procesar_entrada, sanitizar_nombre_archivo


class ProcesamientoTests(unittest.TestCase):
    def test_procesa_patron_valido(self):
        texto = ") 120 H 3\n) 99 M S/E\n) 105 S/S 2"
        datos = procesar_entrada(texto)
        self.assertEqual(datos, [("99", "M", "S/E"), ("105", "S/S", "2"), ("120", "H", "3")])

    def test_sanitiza_nombre_archivo(self):
        nombre = sanitizar_nombre_archivo(' reporte:final*2026?.xlsx ')
        self.assertEqual(nombre, "reporte_final_2026_")


if __name__ == "__main__":
    unittest.main()
