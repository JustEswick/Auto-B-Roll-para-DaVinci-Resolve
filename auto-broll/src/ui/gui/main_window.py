"""
Ventana principal de Auto-B-Roll.

Este módulo define la interfaz gráfica principal de la aplicación.
"""

import sys
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QLabel,
    QFrame,
    QFileDialog,
    QMessageBox,
    QSplitter,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtGui import QIcon, QFont, QAction

# Importar paneles
from .panels import (
    TranscriptionPanel,
    ScriptImportPanel,
    PreviewPanel,
    SettingsPanel,
)


class SidebarButton(QPushButton):
    """Botón personalizado para la barra lateral."""
    
    def __init__(self, text: str, icon_name: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setMinimumHeight(50)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(self._get_style())
    
    def _get_style(self) -> str:
        return """
            QPushButton {
                background-color: transparent;
                color: #E0E0E0;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:checked {
                background-color: #6366F1;
                color: white;
            }
            QPushButton:pressed {
                background-color: #4F46E5;
            }
        """


class Sidebar(QFrame):
    """Barra lateral de navegación."""
    
    page_changed = Signal(int)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border-right: 1px solid #333344;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(8)
        
        # Logo / Título
        title_label = QLabel("🎬 Auto-B-Roll")
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #333344;")
        separator.setMaximumHeight(1)
        layout.addWidget(separator)
        layout.addSpacing(20)
        
        # Botones de navegación
        self.buttons: list[SidebarButton] = []
        
        nav_items = [
            ("📝 Transcripción", 0),
            ("📄 Importar Guion", 1),
            ("🖼️ Preview Assets", 2),
            ("⚙️ Configuración", 3),
        ]
        
        for text, index in nav_items:
            btn = SidebarButton(text)
            btn.clicked.connect(lambda checked, idx=index: self._on_button_clicked(idx))
            self.buttons.append(btn)
            layout.addWidget(btn)
        
        # Seleccionar el primer botón por defecto
        if self.buttons:
            self.buttons[0].setChecked(True)
        
        # Espaciador
        layout.addStretch()
        
        # Versión
        version_label = QLabel("v0.1.0")
        version_label.setStyleSheet("""
            QLabel {
                color: #666677;
                font-size: 12px;
                padding: 10px;
            }
        """)
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
    
    def _on_button_clicked(self, index: int) -> None:
        # Desmarcar todos los botones
        for btn in self.buttons:
            btn.setChecked(False)
        
        # Marcar el botón seleccionado
        self.buttons[index].setChecked(True)
        
        # Emitir señal
        self.page_changed.emit(index)


class StatusBar(QFrame):
    """Barra de estado inferior."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border-top: 1px solid #333344;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        
        # Modo de exportación (script interno)
        self.resolve_status = QLabel("📁 Modo: Script DaVinci")
        self.resolve_status.setStyleSheet("color: #6366F1; font-size: 12px;")
        self.resolve_status.setToolTip(
            "Los assets se exportan como script ejecutable\n"
            "dentro de DaVinci Resolve (compatible con Free)"
        )
        layout.addWidget(self.resolve_status)
        
        layout.addStretch()
        
        # Estado de APIs de Stock
        self.api_status = QLabel("APIs: Verificando...")
        self.api_status.setStyleSheet("color: #888899; font-size: 12px;")
        layout.addWidget(self.api_status)
    
    def set_resolve_connected(self, connected: bool) -> None:
        """Ya no se usa - mantenido por compatibilidad."""
        pass  # No hacemos nada, siempre mostramos modo script
    
    def set_api_status(self, count: int) -> None:
        if count > 0:
            self.api_status.setText(f"✓ {count} API{'s' if count > 1 else ''} de Stock")
            self.api_status.setStyleSheet("color: #4ADE80; font-size: 12px;")
        else:
            self.api_status.setText("⚠️ Configura APIs en ⚙️")
            self.api_status.setStyleSheet("color: #FBBF24; font-size: 12px;")
    
    def refresh_api_status(self) -> None:
        """Refresca el estado de las APIs leyendo la configuración actual."""
        import os
        count = 0
        if os.getenv("PEXELS_API_KEY"):
            count += 1
        if os.getenv("PIXABAY_API_KEY"):
            count += 1
        if os.getenv("UNSPLASH_ACCESS_KEY"):
            count += 1
        self.set_api_status(count)


class MainWindow(QMainWindow):
    """Ventana principal de Auto-B-Roll."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Auto-B-Roll para DaVinci Resolve")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Aplicar estilos globales
        self._apply_global_styles()
        
        # Configurar UI
        self._setup_ui()
        
        # Configurar menú
        self._setup_menu()
        
        # Inicializar estado
        self._init_state()
    
    def _apply_global_styles(self) -> None:
        """Aplica estilos globales a la aplicación."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F0F1A;
            }
            QWidget {
                font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
            }
            QScrollBar:vertical {
                background: #1E1E2E;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #4B5563;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6B7280;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
    
    def _setup_ui(self) -> None:
        """Configura la interfaz de usuario."""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        main_layout.addWidget(self.sidebar)
        
        # Contenedor principal (contenido + status bar)
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Stack de páginas
        self.page_stack = QStackedWidget()
        self.page_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #0F0F1A;
            }
        """)
        
        # Agregar paneles
        self.transcription_panel = TranscriptionPanel()
        self.script_import_panel = ScriptImportPanel()
        self.preview_panel = PreviewPanel()
        self.settings_panel = SettingsPanel()
        
        self.page_stack.addWidget(self.transcription_panel)
        self.page_stack.addWidget(self.script_import_panel)
        self.page_stack.addWidget(self.preview_panel)
        self.page_stack.addWidget(self.settings_panel)
        
        content_layout.addWidget(self.page_stack)
        
        # Status bar
        self.status_bar = StatusBar()
        content_layout.addWidget(self.status_bar)
        
        main_layout.addWidget(content_container)
        
        # Conectar paneles entre sí
        self._connect_panels()
    
    def _connect_panels(self) -> None:
        """Conecta las señales entre paneles."""
        # Cuando el análisis se completa, pasar a búsqueda de assets
        self.transcription_panel.analysis_completed.connect(self._on_analysis_ready)
        
        # Cuando se seleccionan assets, preparar para inserción
        self.preview_panel.assets_selected.connect(self._on_assets_selected)
        
        # Conectar resultados de búsqueda al preview panel
        from src.services import get_services
        services = get_services()
        services.search_finished.connect(self.preview_panel.load_search_results)
    
    @Slot(object)
    def _on_analysis_ready(self, result) -> None:
        """Maneja el resultado del análisis semántico."""
        print(f"[DEBUG] _on_analysis_ready recibido, result: {result}")
        
        # Extraer keywords para búsqueda
        keywords = result.get_unique_search_terms()[:10]
        
        print(f"[DEBUG] Keywords extraídas: {keywords}")
        
        if keywords:
            # Cambiar al panel de preview
            self.sidebar.buttons[2].click()
            
            # Iniciar búsqueda con las keywords
            print(f"[DEBUG] Iniciando búsqueda con {len(keywords)} keywords")
            from src.services import get_services
            services = get_services()
            services.start_search(keywords, asset_type="video", per_keyword=5)
    
    @Slot(list)
    def _on_assets_selected(self, assets) -> None:
        """Maneja los assets seleccionados para inserción."""
        if not assets:
            return
        
        # TODO: Implementar inserción en DaVinci Resolve
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Assets Seleccionados",
            f"Se han seleccionado {len(assets)} assets para inserción.\n\n"
            "La inserción en DaVinci Resolve estará disponible en una próxima versión."
        )
    
    def _setup_menu(self) -> None:
        """Configura el menú de la aplicación."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #1E1E2E;
                color: #E0E0E0;
                padding: 4px;
            }
            QMenuBar::item:selected {
                background-color: #333344;
            }
            QMenu {
                background-color: #1E1E2E;
                color: #E0E0E0;
                border: 1px solid #333344;
            }
            QMenu::item:selected {
                background-color: #6366F1;
            }
        """)
        
        # Menú Archivo
        file_menu = menubar.addMenu("&Archivo")
        
        open_action = QAction("&Abrir Video...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_video)
        file_menu.addAction(open_action)
        
        import_script_action = QAction("&Importar Guion...", self)
        import_script_action.setShortcut("Ctrl+I")
        import_script_action.triggered.connect(self._on_import_script)
        file_menu.addAction(import_script_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Salir", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menú DaVinci
        davinci_menu = menubar.addMenu("&DaVinci")
        
        connect_action = QAction("&Conectar a DaVinci Resolve", self)
        connect_action.triggered.connect(self._on_connect_davinci)
        davinci_menu.addAction(connect_action)
        
        refresh_action = QAction("&Refrescar Timeline", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._on_refresh_timeline)
        davinci_menu.addAction(refresh_action)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("A&yuda")
        
        about_action = QAction("&Acerca de", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _init_state(self) -> None:
        """Inicializa el estado de la aplicación."""
        # TODO: Verificar conexión con DaVinci Resolve
        # TODO: Verificar APIs configuradas
        
        # Por ahora, mostrar estado inicial
        self.status_bar.set_resolve_connected(False)
        self.status_bar.set_api_status(0)
    
    @Slot(int)
    def _on_page_changed(self, index: int) -> None:
        """Maneja el cambio de página."""
        self.page_stack.setCurrentIndex(index)
    
    @Slot()
    def _on_open_video(self) -> None:
        """Abre un archivo de video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Video",
            "",
            "Videos (*.mp4 *.mov *.avi *.mkv);;Todos los archivos (*.*)"
        )
        
        if file_path:
            # TODO: Cargar video y procesar
            self.transcription_panel.load_video(file_path)
    
    @Slot()
    def _on_import_script(self) -> None:
        """Importa un archivo de guion."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar Guion",
            "",
            "Archivos de texto (*.txt *.srt *.md);;Word (*.docx);;Todos los archivos (*.*)"
        )
        
        if file_path:
            # Cambiar al panel de importación de guion
            self.sidebar.buttons[1].click()
            self.script_import_panel.load_script(file_path)
    
    @Slot()
    def _on_connect_davinci(self) -> None:
        """Intenta conectar con DaVinci Resolve."""
        # TODO: Implementar conexión con DaVinci
        QMessageBox.information(
            self,
            "DaVinci Resolve",
            "Funcionalidad de conexión en desarrollo.\n\n"
            "Asegúrate de que DaVinci Resolve esté abierto con un proyecto activo."
        )
    
    @Slot()
    def _on_refresh_timeline(self) -> None:
        """Refresca la información del timeline."""
        # TODO: Implementar refresh
        pass
    
    @Slot()
    def _on_about(self) -> None:
        """Muestra información sobre la aplicación."""
        QMessageBox.about(
            self,
            "Acerca de Auto-B-Roll",
            "<h2>Auto-B-Roll para DaVinci Resolve</h2>"
            "<p>Versión 0.1.0</p>"
            "<p>Automatización inteligente de B-Roll para editores de video.</p>"
            "<p>Analiza el audio de tus videos, entiende el contexto semántico "
            "y busca automáticamente material visual de apoyo.</p>"
            "<hr>"
            "<p><b>Características:</b></p>"
            "<ul>"
            "<li>Transcripción automática con Whisper</li>"
            "<li>Importación de guion para mayor precisión</li>"
            "<li>Búsqueda en APIs de stock gratuitas</li>"
            "<li>Integración nativa con DaVinci Resolve</li>"
            "</ul>"
        )


def run_app() -> int:
    """
    Inicia la aplicación GUI.
    
    Returns:
        Código de salida de la aplicación
    """
    app = QApplication(sys.argv)
    
    # Configurar aplicación
    app.setApplicationName("Auto-B-Roll")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Auto-B-Roll")
    
    # Crear y mostrar ventana principal
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())
