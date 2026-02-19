from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuración del WebDriver (asegúrate de que el path al driver sea correcto)
driver = webdriver.Chrome()

def login():
    driver.get(https://www.snig.gub.uy/)  # Reemplaza con la URL real

    try:
        # Esperar hasta que el campo "usuario" esté interactuable
        usuario_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "usuario"))
        )
        usuario_input.send_keys(208146)  # Reemplaza con el usuario real

        # También podrías hacer lo mismo con la contraseña y el botón de login
        password_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "password"))
        )
        password_input.send_keys(SantaRemigia2026)  # Reemplaza con la contraseña real

        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "boton_login"))  # Ajusta el ID según el botón real
        )
        login_button.click()

    except Exception as e:
        print(f"Error en el login: {e}")
    finally:
        driver.quit()  # Cierra el navegador al finalizar

# Ejecutar la función de login
login()
