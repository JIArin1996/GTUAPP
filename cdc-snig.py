import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


SNIG_URL = os.getenv("SNIG_URL", "https://www.snig.gub.uy/")
SNIG_USER = os.getenv("SNIG_USER")
SNIG_PASSWORD = os.getenv("SNIG_PASSWORD")


def login() -> None:
    if not SNIG_USER or not SNIG_PASSWORD:
        raise ValueError("Definí SNIG_USER y SNIG_PASSWORD como variables de entorno.")

    driver = webdriver.Chrome()
    try:
        driver.get(SNIG_URL)

        usuario_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "usuario"))
        )
        usuario_input.send_keys(SNIG_USER)

        password_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "password"))
        )
        password_input.send_keys(SNIG_PASSWORD)

        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "boton_login"))
        )
        login_button.click()
    finally:
        driver.quit()


if __name__ == "__main__":
    login()
