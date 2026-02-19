# Generador GTU

Aplicación en Python para extraer datos desde un PDF y generar un Excel con columnas `Caravana`, `Sexo` y `Edad`.

## Requisitos

- Python 3.10+
- Dependencias en `requirements.txt`

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

Web local (Flask):

```bash
python pdf_excel_gtu.py
```

App de escritorio (pywebview):

```bash
python app_launcher.py
```

## Build ejecutable (PyInstaller)

```bash
pyinstaller appGTU.spec
```

## Notas

- El Excel se guarda en `~/Downloads`.
- El nombre de archivo se sanitiza para evitar caracteres inválidos en Windows.
- Si el PDF no contiene datos con el formato esperado, la app muestra un error en pantalla.
