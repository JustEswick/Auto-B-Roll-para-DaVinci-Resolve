"""
Panel de Importación de Guion.

Este panel permite importar guiones externos para mejorar
la precisión de la detección de conceptos.
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
    QFrame,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class DropZone(QFrame):
    """Zona de arrastrar y soltar para archivos."""
    
    file_dropped = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border: 2px dashed #4B5563;
                border-radius: 12px;
            }
            QFrame:hover {
                border-color: #6366F1;
                background-color: #1E1E3E;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        text_label = QLabel("Arrastra tu guion aquí")
        text_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 16px;
                font-weight: 500;
            }
        """)
        text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(text_label)
        
        formats_label = QLabel("Formatos soportados: TXT, SRT, DOCX, MD")
        formats_label.setStyleSheet("""
            QLabel {
                color: #6B7280;
                font-size: 12px;
            }
        """)
        formats_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(formats_label)
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame {
                    background-color: #1E1E3E;
                    border: 2px solid #6366F1;
                    border-radius: 12px;
                }
            """)
    
    def dragLeaveEvent(self, event) -> None:
        self._setup_ui()
    
    def dropEvent(self, event: QDropEvent) -> None:
        self._setup_ui()
        
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.file_dropped.emit(file_path)


class ScriptImportPanel(QWidget):
    """Panel para importación de guiones."""
    
    script_loaded = Signal(str)  # Emite el texto del guion
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._script_path: Optional[Path] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz del panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Título
        title = QLabel("📄 Importar Guion")
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
            "Importa el guion de tu video para mejorar la precisión de la transcripción. "
            "El guion se alineará automáticamente con el audio detectado."
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
        
        # Zona de drop
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._on_file_dropped)
        layout.addWidget(self.drop_zone)
        
        # Botón de carga manual
        load_btn_layout = QHBoxLayout()
        load_btn_layout.addStretch()
        
        load_btn = QPushButton("📂 Seleccionar Archivo")
        load_btn.setMinimumHeight(40)
        load_btn.setCursor(Qt.PointingHandCursor)
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #E5E7EB;
                border: 1px solid #4B5563;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4B5563;
                border-color: #6B7280;
            }
        """)
        load_btn.clicked.connect(self._on_load_file)
        load_btn_layout.addWidget(load_btn)
        load_btn_layout.addStretch()
        layout.addLayout(load_btn_layout)
        
        # Información del archivo cargado
        self.file_info_frame = QFrame()
        self.file_info_frame.setVisible(False)
        self.file_info_frame.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        file_info_layout = QHBoxLayout(self.file_info_frame)
        file_info_layout.setContentsMargins(16, 12, 16, 12)
        
        self.file_icon = QLabel("📄")
        self.file_icon.setStyleSheet("font-size: 24px;")
        file_info_layout.addWidget(self.file_icon)
        
        file_details = QVBoxLayout()
        self.file_name_label = QLabel("")
        self.file_name_label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 600;")
        file_details.addWidget(self.file_name_label)
        
        self.file_stats_label = QLabel("")
        self.file_stats_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        file_details.addWidget(self.file_stats_label)
        
        file_info_layout.addLayout(file_details, 1)
        
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(32, 32)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6B7280;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #EF4444;
            }
        """)
        remove_btn.clicked.connect(self._on_remove_file)
        file_info_layout.addWidget(remove_btn)
        
        layout.addWidget(self.file_info_frame)
        
        # Opciones de importación
        options_group = QGroupBox("Opciones de Importación")
        options_group.setStyleSheet("""
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
        
        options_layout = QVBoxLayout(options_group)
        options_layout.setContentsMargins(16, 20, 16, 16)
        options_layout.setSpacing(12)
        
        self.align_checkbox = QCheckBox("Alinear automáticamente con el audio")
        self.align_checkbox.setChecked(True)
        self.align_checkbox.setStyleSheet("""
            QCheckBox {
                color: #E5E7EB;
                font-size: 13px;
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
        options_layout.addWidget(self.align_checkbox)
        
        self.priority_checkbox = QCheckBox("Priorizar texto del guion sobre transcripción")
        self.priority_checkbox.setChecked(True)
        self.priority_checkbox.setStyleSheet("""
            QCheckBox {
                color: #E5E7EB;
                font-size: 13px;
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
        options_layout.addWidget(self.priority_checkbox)
        
        layout.addWidget(options_group)
        
        # Vista previa del contenido
        preview_label = QLabel("Vista Previa del Guion")
        preview_label.setStyleSheet("""
            QLabel {
                color: #E5E7EB;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        layout.addWidget(preview_label)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("El contenido del guion aparecerá aquí...")
        self.preview_text.setStyleSheet("""
            QTextEdit {
                background-color: #0F0F1A;
                color: #E5E7EB;
                border: 1px solid #333344;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.preview_text, 1)
        
        # Botones de acción
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.apply_btn = QPushButton("✓ Aplicar Guion")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setMinimumHeight(44)
        self.apply_btn.setMinimumWidth(160)
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.setStyleSheet("""
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
        self.apply_btn.clicked.connect(self._on_apply)
        actions_layout.addWidget(self.apply_btn)
        
        layout.addLayout(actions_layout)
    
    def load_script(self, file_path: str) -> None:
        """Carga un archivo de guion."""
        path = Path(file_path)
        
        if not path.exists():
            QMessageBox.warning(self, "Error", f"El archivo no existe:\n{file_path}")
            return
        
        # Determinar tipo de archivo y leer contenido
        suffix = path.suffix.lower()
        content = ""
        
        try:
            if suffix in [".txt", ".md", ".srt"]:
                content = path.read_text(encoding="utf-8")
            elif suffix == ".docx":
                # TODO: Implementar lectura de DOCX
                content = f"[Archivo DOCX: {path.name}]\n\nLa lectura de archivos DOCX se implementará próximamente."
            else:
                QMessageBox.warning(
                    self,
                    "Formato no soportado",
                    f"El formato '{suffix}' no está soportado.\n\n"
                    "Formatos válidos: TXT, SRT, DOCX, MD"
                )
                return
        except Exception as e:
            QMessageBox.critical(self, "Error de lectura", f"No se pudo leer el archivo:\n{e}")
            return
        
        self._script_path = path
        
        # Actualizar UI
        self.drop_zone.setVisible(False)
        self.file_info_frame.setVisible(True)
        self.file_name_label.setText(path.name)
        
        word_count = len(content.split())
        line_count = len(content.splitlines())
        self.file_stats_label.setText(f"{word_count} palabras • {line_count} líneas")
        
        self.preview_text.setPlainText(content)
        self.apply_btn.setEnabled(True)
    
    @Slot(str)
    def _on_file_dropped(self, file_path: str) -> None:
        """Maneja archivos soltados en la zona de drop."""
        self.load_script(file_path)
    
    @Slot()
    def _on_load_file(self) -> None:
        """Abre el diálogo de selección de archivo."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Guion",
            "",
            "Archivos de texto (*.txt *.srt *.md);;Word (*.docx);;Todos los archivos (*.*)"
        )
        
        if file_path:
            self.load_script(file_path)
    
    @Slot()
    def _on_remove_file(self) -> None:
        """Elimina el archivo cargado."""
        self._script_path = None
        self.drop_zone.setVisible(True)
        self.file_info_frame.setVisible(False)
        self.preview_text.clear()
        self.apply_btn.setEnabled(False)
    
    @Slot()
    def _on_apply(self) -> None:
        """Aplica el guion cargado."""
        content = self.preview_text.toPlainText()
        if content:
            self.script_loaded.emit(content)
            QMessageBox.information(
                self,
                "Guion Aplicado",
                "El guion se ha cargado correctamente.\n\n"
                "Ahora puedes volver al panel de Transcripción para continuar con el análisis."
            )
