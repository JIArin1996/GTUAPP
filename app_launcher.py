import threading
import webview
from pdf_excel_gtu import app

def iniciar_flask():
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=iniciar_flask)
    flask_thread.daemon = True
    flask_thread.start()

    webview.create_window("GTU - PDF a Excel", "http://127.0.0.1:5000", width=900, height=700)
    webview.start()
