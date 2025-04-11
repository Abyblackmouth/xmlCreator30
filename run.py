import os
import sys
from main import app  # Importa tu aplicación Flask

if __name__ == '__main__':
    # Configura rutas absolutas
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    static_folder = os.path.join(BASE_DIR, 'static')
    template_folder = os.path.join(BASE_DIR, 'templates')
    upload_folder = os.path.join(BASE_DIR, 'uploads')

    # Crea carpetas si no existen
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(static_folder, exist_ok=True)
    os.makedirs(template_folder, exist_ok=True)

    # Ejecuta la aplicación
    app.run(debug=False)