"""
Panel de Configuración.

Este panel permite configurar las preferencias de la aplicación,
API keys y opciones de integración.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFrame,
    QScrollArea,
    QGroupBox,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, Slot


class APIKeyInput(QFrame):
    """Widget de entrada de API key."""
    
    def __init__(
        self,
        name: str,
        description: str,
        current_value: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._name = name
        self._setup_ui(description, current_value)
    
    def _setup_ui(self, description: str, current_value: str) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        name_label = QLabel(self._name)
        name_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_label = QLabel("⚪ No configurado")
        self.status_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Input
        input_layout = QHBoxLayout()
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Ingresa tu API key...")
        self.key_input.setEchoMode(QLineEdit.Password)
        if current_value:
            self.key_input.setText(current_value)
            self._update_status(True)
        self.key_input.setStyleSheet("""
            QLineEdit {
                background-color: #0F0F1A;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
            }
        """)
        self.key_input.textChanged.connect(self._on_text_changed)
        input_layout.addWidget(self.key_input, 1)
        
        # Toggle visibility button
        self.toggle_btn = QPushButton("👁")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                border: none;
                border-radius: 6px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        self.toggle_btn.clicked.connect(self._toggle_visibility)
        input_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(input_layout)
    
    def _toggle_visibility(self) -> None:
        if self.key_input.echoMode() == QLineEdit.Password:
            self.key_input.setEchoMode(QLineEdit.Normal)
            self.toggle_btn.setText("🔒")
        else:
            self.key_input.setEchoMode(QLineEdit.Password)
            self.toggle_btn.setText("👁")
    
    def _on_text_changed(self, text: str) -> None:
        self._update_status(bool(text.strip()))
    
    def _update_status(self, configured: bool) -> None:
        if configured:
            self.status_label.setText("🟢 Configurado")
            self.status_label.setStyleSheet("color: #4ADE80; font-size: 12px;")
        else:
            self.status_label.setText("⚪ No configurado")
            self.status_label.setStyleSheet("color: #6B7280; font-size: 12px;")
    
    def get_value(self) -> str:
        return self.key_input.text().strip()
    
    def set_value(self, value: str) -> None:
        self.key_input.setText(value)


class SettingsPanel(QWidget):
    """Panel de configuración de la aplicación."""
    
    settings_changed = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._load_config()  # Cargar valores guardados
    
    def _setup_ui(self) -> None:
        """Configura la interfaz del panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Título
        title = QLabel("⚙️ Configuración")
        title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #0F0F1A;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #0F0F1A;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #0F0F1A;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 16, 0)
        scroll_layout.setSpacing(24)
        
        # Sección: API Keys
        api_section = self._create_api_section()
        scroll_layout.addWidget(api_section)
        
        # Sección: Whisper
        whisper_section = self._create_whisper_section()
        scroll_layout.addWidget(whisper_section)
        
        # Sección: Búsqueda de Assets
        search_section = self._create_search_section()
        scroll_layout.addWidget(search_section)
        
        # Sección: Timeline
        timeline_section = self._create_timeline_section()
        scroll_layout.addWidget(timeline_section)
        
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)
        
        # Botones de acción
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        reset_btn = QPushButton("Restaurar Valores por Defecto")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9CA3AF;
                border: 1px solid #4B5563;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(75, 85, 99, 0.3);
            }
        """)
        reset_btn.clicked.connect(self._on_reset)
        actions_layout.addWidget(reset_btn)
        
        save_btn = QPushButton("💾 Guardar Configuración")
        save_btn.setMinimumHeight(44)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
            QPushButton:pressed {
                background-color: #4338CA;
            }
        """)
        save_btn.clicked.connect(self._on_save)
        actions_layout.addWidget(save_btn)
        
        layout.addLayout(actions_layout)
    
    def _create_api_section(self) -> QGroupBox:
        """Crea la sección de API keys."""
        import os
        
        group = QGroupBox("🔑 API Keys")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #0F0F1A;
                color: #E5E7EB;
                font-size: 16px;
                font-weight: 600;
                border: 1px solid #333344;
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: #0F0F1A;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(12)
        
        # Cargar valores existentes del entorno
        pexels_key = os.getenv("PEXELS_API_KEY", "")
        pixabay_key = os.getenv("PIXABAY_API_KEY", "")
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
        
        # Pexels
        self.pexels_input = APIKeyInput(
            "Pexels",
            "Obtén tu API key en: https://www.pexels.com/api/",
            current_value=pexels_key
        )
        layout.addWidget(self.pexels_input)
        
        # Pixabay
        self.pixabay_input = APIKeyInput(
            "Pixabay",
            "Obtén tu API key en: https://pixabay.com/api/docs/",
            current_value=pixabay_key
        )
        layout.addWidget(self.pixabay_input)
        
        # Unsplash
        self.unsplash_input = APIKeyInput(
            "Unsplash",
            "Obtén tu Access Key en: https://unsplash.com/developers",
            current_value=unsplash_key
        )
        layout.addWidget(self.unsplash_input)
        
        return group
    
    def _create_whisper_section(self) -> QGroupBox:
        """Crea la sección de configuración de Whisper."""
        group = QGroupBox("🎙️ Transcripción (Whisper)")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #0F0F1A;
                color: #E5E7EB;
                font-size: 16px;
                font-weight: 600;
                border: 1px solid #333344;
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: #0F0F1A;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(16)
        
        # Modelo
        model_layout = QHBoxLayout()
        
        model_label = QLabel("Modelo:")
        model_label.setStyleSheet("color: #E5E7EB; font-size: 14px;")
        model_label.setFixedWidth(120)
        model_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #1E1E2E;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: #6366F1;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E2E;
                color: #E5E7EB;
                selection-background-color: #6366F1;
            }
        """)
        model_layout.addWidget(self.model_combo)
        
        model_hint = QLabel("(base recomendado para balance velocidad/precisión)")
        model_hint.setStyleSheet("color: #6B7280; font-size: 12px;")
        model_layout.addWidget(model_hint)
        model_layout.addStretch()
        
        layout.addLayout(model_layout)
        
        # Idioma
        lang_layout = QHBoxLayout()
        
        lang_label = QLabel("Idioma por defecto:")
        lang_label.setStyleSheet("color: #E5E7EB; font-size: 14px;")
        lang_label.setFixedWidth(120)
        lang_layout.addWidget(lang_label)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Español", "English", "Auto-detectar"])
        self.lang_combo.setCurrentText("Español")
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #1E1E2E;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: #6366F1;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E2E;
                color: #E5E7EB;
                selection-background-color: #6366F1;
            }
        """)
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        
        layout.addLayout(lang_layout)
        
        return group
    
    def _create_search_section(self) -> QGroupBox:
        """Crea la sección de configuración de búsqueda."""
        group = QGroupBox("🔍 Búsqueda de Assets")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #0F0F1A;
                color: #E5E7EB;
                font-size: 16px;
                font-weight: 600;
                border: 1px solid #333344;
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: #0F0F1A;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(16)
        
        # Resultados por API
        results_layout = QHBoxLayout()
        
        results_label = QLabel("Resultados por API:")
        results_label.setStyleSheet("color: #E5E7EB; font-size: 14px;")
        results_label.setFixedWidth(140)
        results_layout.addWidget(results_label)
        
        self.results_spin = QSpinBox()
        self.results_spin.setRange(5, 50)
        self.results_spin.setValue(10)
        self.results_spin.setStyleSheet("""
            QSpinBox {
                background-color: #1E1E2E;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 80px;
            }
            QSpinBox:hover {
                border-color: #6366F1;
            }
        """)
        results_layout.addWidget(self.results_spin)
        results_layout.addStretch()
        
        layout.addLayout(results_layout)
        
        # Tipo preferido
        type_layout = QHBoxLayout()
        
        type_label = QLabel("Tipo preferido:")
        type_label.setStyleSheet("color: #E5E7EB; font-size: 14px;")
        type_label.setFixedWidth(140)
        type_layout.addWidget(type_label)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Videos", "Imágenes", "Ambos"])
        self.type_combo.setCurrentText("Videos")
        self.type_combo.setStyleSheet("""
            QComboBox {
                background-color: #1E1E2E;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: #6366F1;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E2E;
                color: #E5E7EB;
                selection-background-color: #6366F1;
            }
        """)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        
        layout.addLayout(type_layout)
        
        # Orientación
        orient_layout = QHBoxLayout()
        
        orient_label = QLabel("Orientación:")
        orient_label.setStyleSheet("color: #E5E7EB; font-size: 14px;")
        orient_label.setFixedWidth(140)
        orient_layout.addWidget(orient_label)
        
        self.orient_combo = QComboBox()
        self.orient_combo.addItems(["Landscape (16:9)", "Portrait (9:16)", "Square (1:1)"])
        self.orient_combo.setCurrentText("Landscape (16:9)")
        self.orient_combo.setStyleSheet("""
            QComboBox {
                background-color: #1E1E2E;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: #6366F1;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E2E;
                color: #E5E7EB;
                selection-background-color: #6366F1;
            }
        """)
        orient_layout.addWidget(self.orient_combo)
        orient_layout.addStretch()
        
        layout.addLayout(orient_layout)
        
        return group
    
    def _create_timeline_section(self) -> QGroupBox:
        """Crea la sección de configuración de timeline."""
        group = QGroupBox("🎬 Timeline")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #0F0F1A;
                color: #E5E7EB;
                font-size: 16px;
                font-weight: 600;
                border: 1px solid #333344;
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                background-color: #0F0F1A;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(16)
        
        # Duración de clip
        duration_layout = QHBoxLayout()
        
        duration_label = QLabel("Duración por clip:")
        duration_label.setStyleSheet("color: #E5E7EB; font-size: 14px;")
        duration_label.setFixedWidth(140)
        duration_layout.addWidget(duration_label)
        
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(1.0, 10.0)
        self.duration_spin.setValue(3.0)
        self.duration_spin.setSuffix(" seg")
        self.duration_spin.setSingleStep(0.5)
        self.duration_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #1E1E2E;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 100px;
            }
            QDoubleSpinBox:hover {
                border-color: #6366F1;
            }
        """)
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()
        
        layout.addLayout(duration_layout)
        
        # Track de destino
        track_layout = QHBoxLayout()
        
        track_label = QLabel("Track de destino:")
        track_label.setStyleSheet("color: #E5E7EB; font-size: 14px;")
        track_label.setFixedWidth(140)
        track_layout.addWidget(track_label)
        
        self.track_spin = QSpinBox()
        self.track_spin.setRange(1, 10)
        self.track_spin.setValue(2)
        self.track_spin.setStyleSheet("""
            QSpinBox {
                background-color: #1E1E2E;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 80px;
            }
            QSpinBox:hover {
                border-color: #6366F1;
            }
        """)
        track_layout.addWidget(self.track_spin)
        
        track_hint = QLabel("(Track 2 recomendado para B-Roll)")
        track_hint.setStyleSheet("color: #6B7280; font-size: 12px;")
        track_layout.addWidget(track_hint)
        track_layout.addStretch()
        
        layout.addLayout(track_layout)
        
        # Auto-insert
        self.auto_insert_check = QCheckBox("Insertar automáticamente sin confirmación")
        self.auto_insert_check.setStyleSheet("""
            QCheckBox {
                color: #E5E7EB;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #4B5563;
                background-color: #1E1E2E;
            }
            QCheckBox::indicator:checked {
                background-color: #6366F1;
                border-color: #6366F1;
            }
        """)
        layout.addWidget(self.auto_insert_check)
        
        return group
    
    def _load_config(self) -> None:
        """Carga la configuración guardada en los widgets."""
        try:
            from src.config import get_config
            config = get_config()
            
            # Whisper
            if config.whisper.model:
                self.model_combo.setCurrentText(config.whisper.model)
            
            # Idioma - convertir de código a nombre
            lang_reverse_map = {"es": "Español", "en": "English", None: "Auto-detectar"}
            if config.whisper.language in lang_reverse_map:
                self.lang_combo.setCurrentText(lang_reverse_map[config.whisper.language])
            
            # Search
            if config.search.results_per_api:
                self.results_spin.setValue(config.search.results_per_api)
            
            # Tipo preferido
            type_map_reverse = {"video": "Videos", "image": "Imágenes", "all": "Ambos"}
            if config.search.preferred_type in type_map_reverse:
                self.type_combo.setCurrentText(type_map_reverse[config.search.preferred_type])
            
            # Orientación
            orient_map_reverse = {
                "landscape": "Landscape (16:9)",
                "portrait": "Portrait (9:16)",
                "square": "Square (1:1)"
            }
            if config.search.preferred_orientation in orient_map_reverse:
                self.orient_combo.setCurrentText(orient_map_reverse[config.search.preferred_orientation])
            
            # Timeline
            if config.timeline.default_clip_duration:
                self.duration_spin.setValue(config.timeline.default_clip_duration)
            if config.timeline.target_track:
                self.track_spin.setValue(config.timeline.target_track)
            if hasattr(config.timeline, 'auto_insert'):
                self.auto_insert_check.setChecked(config.timeline.auto_insert)
                
        except Exception as e:
            # Si falla la carga, usar valores por defecto (ya están en los widgets)
            pass  # Usar valores por defecto si falla la carga
    
    @Slot()
    def _on_reset(self) -> None:
        """Restaura los valores por defecto."""
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Estás seguro de que deseas restaurar todos los valores por defecto?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.model_combo.setCurrentText("base")
            self.lang_combo.setCurrentText("Español")
            self.results_spin.setValue(10)
            self.type_combo.setCurrentText("Videos")
            self.orient_combo.setCurrentText("Landscape (16:9)")
            self.duration_spin.setValue(3.0)
            self.track_spin.setValue(2)
            self.auto_insert_check.setChecked(False)
    
    @Slot()
    def _on_save(self) -> None:
        """Guarda la configuración."""
        from pathlib import Path
        import os
        
        # Obtener directorio del proyecto
        project_root = Path(__file__).parent.parent.parent.parent.parent
        env_file = project_root / ".env"
        
        # Leer .env existente (si hay)
        env_vars = {}
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
        
        # Actualizar con los nuevos valores
        pexels_key = self.pexels_input.get_value()
        pixabay_key = self.pixabay_input.get_value()
        unsplash_key = self.unsplash_input.get_value()
        
        if pexels_key:
            env_vars["PEXELS_API_KEY"] = pexels_key
            os.environ["PEXELS_API_KEY"] = pexels_key
        if pixabay_key:
            env_vars["PIXABAY_API_KEY"] = pixabay_key
            os.environ["PIXABAY_API_KEY"] = pixabay_key
        if unsplash_key:
            env_vars["UNSPLASH_ACCESS_KEY"] = unsplash_key
            os.environ["UNSPLASH_ACCESS_KEY"] = unsplash_key
        
        # Escribir archivo .env
        try:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write("# Auto-B-Roll - API Keys\n")
                f.write("# Generado automáticamente\n\n")
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            
            # Actualizar la configuración global en memoria
            from src.config import get_config
            config = get_config()
            config.api_keys.pexels = pexels_key if pexels_key else None
            config.api_keys.pixabay = pixabay_key if pixabay_key else None
            config.api_keys.unsplash = unsplash_key if unsplash_key else None
            
            # Guardar otras configuraciones
            config.whisper.model = self.model_combo.currentText()
            lang_map = {"Español": "es", "English": "en", "Auto-detectar": None}
            config.whisper.language = lang_map.get(self.lang_combo.currentText(), "es")
            
            # Search
            config.search.results_per_api = self.results_spin.value()
            type_map = {"Videos": "video", "Imágenes": "image", "Ambos": "all"}
            config.search.preferred_type = type_map.get(self.type_combo.currentText(), "video")
            orient_map = {
                "Landscape (16:9)": "landscape",
                "Portrait (9:16)": "portrait",
                "Square (1:1)": "square"
            }
            config.search.preferred_orientation = orient_map.get(self.orient_combo.currentText(), "landscape")
            
            # Timeline
            config.timeline.default_clip_duration = self.duration_spin.value()
            config.timeline.target_track = self.track_spin.value()
            config.timeline.auto_insert = self.auto_insert_check.isChecked()
            config.save()
            
            QMessageBox.information(
                self,
                "Configuración Guardada",
                "La configuración se ha guardado correctamente.\n\n"
                f"APIs configuradas:\n"
                f"• Pexels: {'✓' if pexels_key else '✗'}\n"
                f"• Pixabay: {'✓' if pixabay_key else '✗'}\n"
                f"• Unsplash: {'✓' if unsplash_key else '✗'}"
            )
            self.settings_changed.emit()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo guardar la configuración:\n{e}"
            )

