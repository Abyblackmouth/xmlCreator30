import os
from main import app

if __name__ == '__main__':
    # Crear carpetas necesarias si no existen
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    # Ejecutar la aplicación
    app.run(debug=False)