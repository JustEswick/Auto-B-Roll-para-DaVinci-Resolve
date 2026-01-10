"""
Punto de entrada principal de Auto-B-Roll.

Este módulo inicializa la aplicación y lanza la interfaz gráfica.
"""

import sys
from pathlib import Path

# Asegurar que el directorio src esté en el path
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from config import init_directories, get_config


def main() -> int:
    """
    Función principal de la aplicación.
    
    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    # Inicializar directorios
    init_directories()
    
    # Cargar configuración
    config = get_config()
    
    # Importar y lanzar GUI
    from ui.gui.main_window import run_app
    
    return run_app()


if __name__ == "__main__":
    sys.exit(main())
