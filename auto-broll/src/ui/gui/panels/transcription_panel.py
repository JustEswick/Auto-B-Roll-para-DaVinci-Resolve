"""
Panel de Transcripción.

Este panel muestra la transcripción del audio y permite
analizar el video para extraer conceptos visualizables.
"""

from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QFrame,
    QScrollArea,
    QFileDialog,
    QComboBox,
    QGroupBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtGui import QFont


class TranscriptionPanel(QWidget):
    """Panel para transcripción de audio."""
    
    transcription_completed = Signal(str)  # Emite el texto transcrito
    analysis_completed = Signal(object)  # Emite el resultado del análisis
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._video_path: Optional[Path] = None
        self._transcription = None
        self._connect_services()
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz del panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Título
        title = QLabel("📝 Transcripción de Audio")
        title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)
        
        # Descripción
        description = QLabel(
            "Carga un video para transcribir automáticamente el audio usando Whisper. "
            "La transcripción se utilizará para identificar conceptos visualizables."
        )
        description.setWordWrap(True)
        description.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        layout.addWidget(description)
        
        # Sección de carga de video
        load_section = self._create_load_section()
        layout.addWidget(load_section)
        
        # Opciones de transcripción
        options_section = self._create_options_section()
        layout.addWidget(options_section)
        
        # Área de transcripción
        transcription_section = self._create_transcription_section()
        layout.addWidget(transcription_section, 1)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E1E2E;
                border: none;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #6366F1;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Botones de acción
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.transcribe_btn = QPushButton("🎙️ Iniciar Transcripción")
        self.transcribe_btn.setEnabled(False)
        self.transcribe_btn.setMinimumHeight(44)
        self.transcribe_btn.setMinimumWidth(200)
        self.transcribe_btn.setCursor(Qt.PointingHandCursor)
        self.transcribe_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #374151;
                color: #6B7280;
            }
        """)
        self.transcribe_btn.clicked.connect(self._on_transcribe)
        actions_layout.addWidget(self.transcribe_btn)
        
        self.analyze_btn = QPushButton("🧠 Analizar Conceptos")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setMinimumHeight(44)
        self.analyze_btn.setMinimumWidth(180)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6B7280;
            }
        """)
        self.analyze_btn.clicked.connect(self._on_analyze)
        actions_layout.addWidget(self.analyze_btn)
        
        layout.addLayout(actions_layout)
    
    def _create_load_section(self) -> QFrame:
        """Crea la sección de carga de video."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # Icono y label
        icon_label = QLabel("🎬")
        icon_label.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon_label)
        
        # Info del video
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.video_name_label = QLabel("Ningún video seleccionado")
        self.video_name_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        info_layout.addWidget(self.video_name_label)
        
        self.video_info_label = QLabel("Arrastra un video aquí o haz clic en 'Cargar Video'")
        self.video_info_label.setStyleSheet("""
            QLabel {
                color: #6B7280;
                font-size: 13px;
            }
        """)
        info_layout.addWidget(self.video_info_label)
        
        layout.addLayout(info_layout, 1)
        
        # Botón de carga
        load_btn = QPushButton("📂 Cargar Video")
        load_btn.setMinimumHeight(40)
        load_btn.setCursor(Qt.PointingHandCursor)
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                border: 1px solid #4B5563;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4B5563;
                border-color: #6B7280;
            }
        """)
        load_btn.clicked.connect(self._on_load_video)
        layout.addWidget(load_btn)
        
        return frame
    
    def _create_options_section(self) -> QGroupBox:
        """Crea la sección de opciones de transcripción."""
        group = QGroupBox("Opciones de Transcripción")
        group.setStyleSheet("""
            QGroupBox {
                color: #E5E7EB;
                font-size: 14px;
                font-weight: 600;
                border: 1px solid #333344;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }
        """)
        
        layout = QHBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(24)
        
        # Modelo Whisper
        model_layout = QVBoxLayout()
        model_label = QLabel("Modelo Whisper:")
        model_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        model_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #374151;
                color: #E5E7EB;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #6366F1;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E2E;
                color: #E5E7EB;
                selection-background-color: #6366F1;
            }
        """)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        # Idioma
        lang_layout = QVBoxLayout()
        lang_label = QLabel("Idioma:")
        lang_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        lang_layout.addWidget(lang_label)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Español", "English", "Auto-detectar"])
        self.lang_combo.setCurrentText("Español")
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #374151;
                color: #E5E7EB;
                border: 1px solid #4B5563;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 140px;
            }
            QComboBox:hover {
                border-color: #6366F1;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E2E;
                color: #E5E7EB;
                selection-background-color: #6366F1;
            }
        """)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)
        
        layout.addStretch()
        
        return group
    
    def _create_transcription_section(self) -> QFrame:
        """Crea la sección de texto de transcripción."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Transcripción")
        header_label.setStyleSheet("""
            QLabel {
                color: #E5E7EB;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        self.word_count_label = QLabel("0 palabras")
        self.word_count_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        header_layout.addWidget(self.word_count_label)
        
        layout.addLayout(header_layout)
        
        # Área de texto
        self.transcription_text = QTextEdit()
        self.transcription_text.setPlaceholderText(
            "La transcripción aparecerá aquí después de procesar el video...\n\n"
            "También puedes pegar texto manualmente o importar un guion desde el panel 'Importar Guion'."
        )
        self.transcription_text.setStyleSheet("""
            QTextEdit {
                background-color: #0F0F1A;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border-color: #6366F1;
            }
        """)
        self.transcription_text.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.transcription_text)
        
        return frame
    
    def _connect_services(self) -> None:
        """Conecta con los servicios de backend."""
        from src.services import get_services
        
        services = get_services()
        
        # Conectar señales de transcripción
        services.transcription_progress.connect(self._on_transcription_progress)
        services.transcription_finished.connect(self._on_transcription_finished)
        services.transcription_error.connect(self._on_transcription_error)
        
        # Conectar señales de análisis
        services.analysis_finished.connect(self._on_analysis_finished)
        services.analysis_error.connect(self._on_analysis_error)
    
    def load_video(self, file_path: str) -> None:
        """Carga un archivo de video."""
        path = Path(file_path)
        if path.exists():
            self._video_path = path
            self.video_name_label.setText(path.name)
            self.video_info_label.setText(f"📍 {path.parent}")
            self.transcribe_btn.setEnabled(True)
    
    @Slot()
    def _on_load_video(self) -> None:
        """Maneja la carga de video."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Video",
            "",
            "Videos (*.mp4 *.mov *.avi *.mkv *.webm);;Todos los archivos (*.*)"
        )
        
        if file_path:
            self.load_video(file_path)
    
    @Slot()
    def _on_transcribe(self) -> None:
        """Inicia el proceso de transcripción."""
        if not self._video_path:
            return
        
        from src.services import get_services
        
        # Obtener configuración
        model = self.model_combo.currentText()
        lang_text = self.lang_combo.currentText()
        language_map = {"Español": "es", "English": "en", "Auto-detectar": None}
        language = language_map.get(lang_text, "es")
        
        # Actualizar UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.transcribe_btn.setEnabled(False)
        self.transcribe_btn.setText("⏳ Transcribiendo...")
        
        # Iniciar transcripción
        services = get_services()
        services.start_transcription(self._video_path, model, language)
    
    @Slot(float, str)
    def _on_transcription_progress(self, progress: float, message: str) -> None:
        """Actualiza el progreso de transcripción."""
        self.progress_bar.setValue(int(progress * 100))
        self.video_info_label.setText(message)
    
    @Slot(object)
    def _on_transcription_finished(self, transcription) -> None:
        """Maneja la transcripción completada."""
        self._transcription = transcription
        
        # Mostrar texto
        self.transcription_text.setPlainText(transcription.full_text)
        
        # Restaurar UI
        self.progress_bar.setVisible(False)
        self.transcribe_btn.setEnabled(True)
        self.transcribe_btn.setText("🎙️ Iniciar Transcripción")
        self.analyze_btn.setEnabled(True)
        
        self.video_info_label.setText(
            f"✅ Transcripción completada - {transcription.word_count} palabras, "
            f"{len(transcription.segments)} segmentos"
        )
        
        # Emitir señal
        self.transcription_completed.emit(transcription.full_text)
    
    @Slot(str)
    def _on_transcription_error(self, error: str) -> None:
        """Maneja errores de transcripción."""
        self.progress_bar.setVisible(False)
        self.transcribe_btn.setEnabled(True)
        self.transcribe_btn.setText("🎙️ Iniciar Transcripción")
        
        QMessageBox.critical(
            self,
            "Error de Transcripción",
            f"Ocurrió un error durante la transcripción:\n\n{error}"
        )
    
    @Slot()
    def _on_analyze(self) -> None:
        """Analiza el texto para extraer conceptos."""
        text = self.transcription_text.toPlainText()
        if not text.strip():
            return
        
        from src.services import get_services
        
        # Obtener timestamps si hay transcripción
        timestamps = None
        if self._transcription and self._transcription.segments:
            timestamps = [
                (seg.start, seg.end, seg.text)
                for seg in self._transcription.segments
            ]
        
        # Determinar idioma
        lang_text = self.lang_combo.currentText()
        language_map = {"Español": "es", "English": "en", "Auto-detectar": "es"}
        language = language_map.get(lang_text, "es")
        
        # Iniciar análisis
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("⏳ Analizando...")
        
        services = get_services()
        services.start_analysis(text, timestamps, language)
    
    @Slot(object)
    def _on_analysis_finished(self, result) -> None:
        """Maneja el análisis completado."""
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("🧠 Analizar Conceptos")
        
        # Emitir señal con el resultado
        self.analysis_completed.emit(result)
        
        # Mostrar resumen
        concepts_count = len(result.concepts)
        keywords = result.get_unique_search_terms()[:5]
        
        QMessageBox.information(
            self,
            "Análisis Completado",
            f"Se encontraron {concepts_count} conceptos visualizables.\n\n"
            f"Keywords principales:\n• " + "\n• ".join(keywords[:5])
        )
    
    @Slot(str)
    def _on_analysis_error(self, error: str) -> None:
        """Maneja errores de análisis."""
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("🧠 Analizar Conceptos")
        
        QMessageBox.critical(
            self,
            "Error de Análisis",
            f"Ocurrió un error durante el análisis:\n\n{error}"
        )
    
    @Slot()
    def _on_text_changed(self) -> None:
        """Actualiza el contador de palabras."""
        text = self.transcription_text.toPlainText()
        word_count = len(text.split()) if text.strip() else 0
        self.word_count_label.setText(f"{word_count} palabras")
        self.analyze_btn.setEnabled(word_count > 0)

