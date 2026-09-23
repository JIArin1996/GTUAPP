import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

load_dotenv()

SNIG_URL_PORTADA = "https://www.snig.gub.uy/"
SNIG_URL_PRODUCTOR = "https://www.snig.gub.uy/productor"
STORAGE_STATE_PATH = Path(__file__).resolve().parent / "snig_storage_state.json"

# Selectores confirmados contra el sitio real (formulario de login en la portada).
# Se usa `name` porque los `id` empiezan con un numero y no son selectores CSS validos.
SELECTOR_USUARIO = "[name=login_1_field_1]"
SELECTOR_CLAVE = "[name=login_1_field_2]"
SELECTOR_CODIGO = "[name=login_1_field_3]"
TEXTO_BOTON_INGRESO = "Iniciar sesión"
TEXTO_ERROR_LOGIN = "Dato no válido"
TEXTO_BOTON_SALIR = "Salir"

TIMEOUT_MS = 30_000


class SnigLoginError(Exception):
    """Error base del login a SNIG."""


class SnigCredencialesFaltantes(SnigLoginError):
    pass


class SnigCredencialesInvalidas(SnigLoginError):
    pass


class SnigCodigoRequerido(SnigLoginError):
    pass


class SnigSinRespuesta(SnigLoginError):
    pass


def _headless() -> bool:
    return os.getenv("SNIG_HEADLESS", "true").strip().lower() not in ("false", "0", "no")


def _sesion_activa(page) -> bool:
    respuesta = page.goto(SNIG_URL_PRODUCTOR, wait_until="networkidle", timeout=TIMEOUT_MS)
    if respuesta is None or respuesta.status != 200:
        return False
    return page.get_by_text(TEXTO_BOTON_SALIR, exact=True).count() > 0


def _visible(page, locator) -> bool:
    try:
        return locator.is_visible()
    except PlaywrightError:
        # La pagina puede estar navegando en ese instante.
        return False


def _hacer_login(page, usuario: str, clave: str) -> None:
    page.goto(SNIG_URL_PORTADA, wait_until="networkidle", timeout=TIMEOUT_MS)
    page.fill(SELECTOR_USUARIO, usuario)
    page.fill(SELECTOR_CLAVE, clave)
    page.get_by_role("button", name=TEXTO_BOTON_INGRESO).click()

    error = page.get_by_text(TEXTO_ERROR_LOGIN)
    codigo = page.locator(SELECTOR_CODIGO)
    limite = time.monotonic() + TIMEOUT_MS / 1000
    while time.monotonic() < limite:
        if "/productor" in page.url:
            page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
            return
        if _visible(page, error):
            raise SnigCredencialesInvalidas("SNIG rechazó el usuario o la contraseña (\"Dato no válido\").")
        if _visible(page, codigo):
            raise SnigCodigoRequerido("SNIG pide un código adicional para ingresar; el login automático no lo soporta.")
        page.wait_for_timeout(250)
    raise SnigSinRespuesta("SNIG no respondió al login dentro del tiempo esperado.")


def iniciar_sesion_snig(forzar_login: bool = False) -> Path:
    usuario = os.getenv("SNIG_USER")
    clave = os.getenv("SNIG_PASS")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=_headless())
        try:
            if STORAGE_STATE_PATH.exists() and not forzar_login:
                context = browser.new_context(storage_state=str(STORAGE_STATE_PATH))
                try:
                    if _sesion_activa(context.new_page()):
                        return STORAGE_STATE_PATH
                except PlaywrightError:
                    pass
                finally:
                    context.close()

            if not usuario or not clave:
                raise SnigCredencialesFaltantes("Faltan SNIG_USER y/o SNIG_PASS en el .env.")

            context = browser.new_context()
            try:
                page = context.new_page()
                try:
                    _hacer_login(page, usuario, clave)
                except PlaywrightError as exc:
                    # No se propaga el mensaje de Playwright: puede incluir los valores tipeados.
                    raise SnigSinRespuesta(
                        f"Falló la interacción con SNIG ({type(exc).__name__}). "
                        "Probá con SNIG_HEADLESS=false para ver qué pasa."
                    ) from None
                context.storage_state(path=str(STORAGE_STATE_PATH))
            finally:
                context.close()
            return STORAGE_STATE_PATH
        finally:
            browser.close()


if __name__ == "__main__":
    import sys

    forzar = "--forzar" in sys.argv
    mtime_previo = STORAGE_STATE_PATH.stat().st_mtime if STORAGE_STATE_PATH.exists() else None
    try:
        ruta = iniciar_sesion_snig(forzar_login=forzar)
    except SnigLoginError as exc:
        print(f"Login SNIG fallido: {exc}")
        sys.exit(1)
    modo = "sesión guardada reutilizada" if ruta.stat().st_mtime == mtime_previo else "login nuevo"
    print(f"Login SNIG OK ({modo}). Sesión en: {ruta}")
