# Generador GTU (Web)

Aplicación web en Python (Flask) para extraer datos desde un PDF y generar un Excel con columnas `Caravana`, `Sexo` y `Edad`.

## Requisitos

- Python 3.10+
- Dependencias en `requirements.txt`

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución local

```bash
python pdf_excel_gtu.py
```

Luego abrí en el navegador:

```text
http://127.0.0.1:5000
```

## Notas

- El Excel se guarda en `~/Downloads`.
- El nombre de archivo se sanitiza para evitar caracteres inválidos en Windows.
- Si el PDF no contiene datos con el formato esperado, la app muestra un error en pantalla.
