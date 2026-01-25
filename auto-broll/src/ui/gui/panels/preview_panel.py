"""
Panel de Preview de Assets.

Este panel muestra los assets encontrados para cada concepto
y permite al usuario aprobar o rechazar las sugerencias.
"""

from typing import Optional, List
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QGridLayout,
    QSizePolicy,
    QProgressBar,
    QLineEdit,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal, Slot, QSize, QThread, QByteArray
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from urllib.request import urlopen
import ssl


@dataclass
class AssetPreview:
    """Datos de un asset para preview."""
    id: str
    source: str  # pexels, pixabay, unsplash
    type: str  # image, video
    thumbnail_url: str
    preview_url: str
    keyword: str
    selected: bool = False


class ThumbnailLoader(QThread):
    """Worker para cargar thumbnails de forma asíncrona."""
    
    loaded = Signal(str, bytes)  # asset_id, image_data
    error = Signal(str)  # error message
    
    def __init__(self, asset_id: str, url: str, parent=None):
        super().__init__(parent)
        self._asset_id = asset_id
        self._url = url
    
    def run(self):
        try:
            from urllib.request import Request
            from src.config import get_config
            
            # Crear request con headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Agregar API key de Pexels si es URL de Pexels
            if 'pexels.com' in self._url:
                config = get_config()
                if config.api_keys.pexels:
                    headers['Authorization'] = config.api_keys.pexels
            
            request = Request(self._url, headers=headers)
            
            # Crear contexto SSL que ignora verificación
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urlopen(request, timeout=10, context=ctx) as response:
                data = response.read()
                self.loaded.emit(self._asset_id, data)
        except Exception as e:
            self.error.emit(str(e))


class AssetCard(QFrame):
    """Tarjeta de preview de un asset."""
    
    selection_changed = Signal(str, bool)  # id, selected
    
    def __init__(
        self,
        asset_id: str,
        keyword: str,
        source: str,
        asset_type: str,
        thumbnail_url: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._asset_id = asset_id
        self._selected = False
        self._thumbnail_url = thumbnail_url
        self._loader = None
        self._setup_ui(keyword, source, asset_type)
        
        # Cargar thumbnail si hay URL
        if thumbnail_url:
            self._load_thumbnail()
    
    def _setup_ui(self, keyword: str, source: str, asset_type: str) -> None:
        self.setFixedSize(280, 240)  # Tamaño amplio
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Área de thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(256, 150)  # Thumbnail grande
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #0F0F1A;
                border-radius: 8px;
                color: #6B7280;
                font-size: 48px;
            }
        """)
        # Placeholder icon
        icon = "🎬" if asset_type == "video" else "🖼️"
        self.thumbnail_label.setText(icon)
        layout.addWidget(self.thumbnail_label)
        
        # Info
        info_layout = QHBoxLayout()
        info_layout.setSpacing(6)
        
        # Source badge (primero para visibilidad)
        source_colors = {
            "pexels": "#07A081",
            "pixabay": "#6BB338",
            "unsplash": "#000000",
        }
        source_badge = QLabel(source.upper())
        source_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {source_colors.get(source, '#4B5563')};
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
            }}
        """)
        info_layout.addWidget(source_badge)
        
        # Tipo de asset
        type_icon = "🎬" if asset_type == "video" else "🖼️"
        type_label = QLabel(f"{type_icon} {'Video' if asset_type == 'video' else 'Imagen'}")
        type_label.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 11px;
            }
        """)
        info_layout.addWidget(type_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Checkbox indicador de selección
        self.select_hint = QLabel("Click para seleccionar")
        self.select_hint.setStyleSheet("""
            QLabel {
                color: #6B7280;
                font-size: 10px;
                font-style: italic;
            }
        """)
        self.select_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.select_hint)
    
    def _update_style(self) -> None:
        if self._selected:
            self.setStyleSheet("""
                QFrame {
                    background-color: #1E1E2E;
                    border: 2px solid #6366F1;
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #1E1E2E;
                    border: 2px solid transparent;
                    border-radius: 10px;
                }
                QFrame:hover {
                    border-color: #4B5563;
                }
            """)
    
    def mousePressEvent(self, event) -> None:
        self._selected = not self._selected
        self._update_style()
        self.selection_changed.emit(self._asset_id, self._selected)
    
    @property
    def is_selected(self) -> bool:
        return self._selected
    
    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._update_style()
    
    def _load_thumbnail(self) -> None:
        """Inicia la carga del thumbnail."""
        print(f"[THUMB] Cargando: {self._thumbnail_url[:80]}...")
        self._loader = ThumbnailLoader(self._asset_id, self._thumbnail_url, self)
        self._loader.loaded.connect(self._on_thumbnail_loaded)
        self._loader.error.connect(self._on_thumbnail_error)
        self._loader.start()
    
    @Slot(str)
    def _on_thumbnail_error(self, error: str) -> None:
        """Maneja errores de carga."""
        print(f"[THUMB ERROR] {self._asset_id}: {error}")
    
    @Slot(str, bytes)
    def _on_thumbnail_loaded(self, asset_id: str, data: bytes) -> None:
        """Muestra el thumbnail cuando se carga."""
        print(f"[THUMB OK] {asset_id}, bytes: {len(data)}")
        if asset_id != self._asset_id:
            return
        
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            # Escalar manteniendo proporción
            scaled = pixmap.scaled(
                256, 150,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.thumbnail_label.setPixmap(scaled)
            self.thumbnail_label.setText("")
        else:
            print(f"[THUMB] No se pudo crear pixmap")
        self._loader = None


class ManualKeywordItem(QFrame):
    """Widget para una keyword manual en la lista."""
    
    selection_changed = Signal(str, bool)  # keyword, selected
    delete_requested = Signal(str)  # keyword
    
    def __init__(self, keyword: str, timestamp: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._keyword = keyword
        self._timestamp = timestamp
        self._selected = True  # Seleccionado por defecto
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #6366F1;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #374151;
                border-radius: 4px;
            }
        """)
        self.checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self.checkbox)
        
        # Keyword label
        keyword_label = QLabel(self._keyword)
        keyword_label.setStyleSheet("color: #FFFFFF; font-size: 13px;")
        layout.addWidget(keyword_label, 1)
        
        # Timestamp label
        time_text = self._timestamp if self._timestamp else "-"
        time_label = QLabel(time_text)
        time_label.setStyleSheet("color: #6B7280; font-size: 12px; min-width: 50px;")
        time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(time_label)
        
        # Delete button
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                border-radius: 4px;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._keyword))
        layout.addWidget(delete_btn)
    
    def _on_toggled(self, checked: bool) -> None:
        self._selected = checked
        self.selection_changed.emit(self._keyword, checked)
    
    @property
    def keyword(self) -> str:
        return self._keyword
    
    @property
    def timestamp(self) -> str:
        return self._timestamp
    
    @property
    def is_selected(self) -> bool:
        return self._selected


class ManualKeywordsSection(QFrame):
    """Sección para agregar y gestionar keywords manuales."""
    
    search_requested = Signal(list)  # Lista de dicts con keyword y timestamp
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._keyword_items: List[ManualKeywordItem] = []
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #13131A;
                border: 1px solid #2D2D44;
                border-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("➕ Agregar Keywords Manuales")
        header.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        layout.addWidget(header)
        
        # Input row
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: transparent; border: none;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        
        # Keyword input
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("Escribe una palabra clave...")
        self.keyword_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E2E;
                color: #FFFFFF;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
            }
        """)
        self.keyword_input.returnPressed.connect(self._on_add_keyword)
        input_layout.addWidget(self.keyword_input, 2)
        
        # Timestamp input
        time_label = QLabel("Tiempo:")
        time_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        input_layout.addWidget(time_label)
        
        self.timestamp_input = QLineEdit()
        self.timestamp_input.setPlaceholderText("00:00")
        self.timestamp_input.setMaximumWidth(70)
        self.timestamp_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E2E;
                color: #FFFFFF;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
            }
        """)
        self.timestamp_input.returnPressed.connect(self._on_add_keyword)
        input_layout.addWidget(self.timestamp_input)
        
        # Add button
        add_btn = QPushButton("+ Agregar")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4B5563;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #6B7280;
            }
        """)
        add_btn.clicked.connect(self._on_add_keyword)
        input_layout.addWidget(add_btn)
        
        layout.addWidget(input_frame)
        
        # Keywords list container
        self.keywords_container = QWidget()
        self.keywords_layout = QVBoxLayout(self.keywords_container)
        self.keywords_layout.setContentsMargins(0, 0, 0, 0)
        self.keywords_layout.setSpacing(6)
        self.keywords_container.setVisible(False)
        layout.addWidget(self.keywords_container)
        
        # Search button
        self.search_btn = QPushButton("🔍 Buscar Assets")
        self.search_btn.setEnabled(False)
        self.search_btn.setMinimumHeight(40)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5558E3;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6B7280;
            }
        """)
        self.search_btn.clicked.connect(self._on_search)
        layout.addWidget(self.search_btn)
    
    @Slot()
    def _on_add_keyword(self) -> None:
        """Agrega una keyword a la lista."""
        keyword = self.keyword_input.text().strip()
        if not keyword:
            return
        
        # Evitar duplicados
        existing = [item.keyword.lower() for item in self._keyword_items]
        if keyword.lower() in existing:
            self.keyword_input.clear()
            return
        
        timestamp = self.timestamp_input.text().strip()
        
        item = ManualKeywordItem(keyword, timestamp)
        item.selection_changed.connect(self._update_search_button)
        item.delete_requested.connect(self._on_delete_keyword)
        
        self._keyword_items.append(item)
        self.keywords_layout.addWidget(item)
        
        self.keywords_container.setVisible(True)
        self.keyword_input.clear()
        self.timestamp_input.clear()
        self.keyword_input.setFocus()
        
        self._update_search_button()
    
    @Slot(str)
    def _on_delete_keyword(self, keyword: str) -> None:
        """Elimina una keyword de la lista."""
        for item in self._keyword_items[:]:
            if item.keyword == keyword:
                self._keyword_items.remove(item)
                item.deleteLater()
                break
        
        if not self._keyword_items:
            self.keywords_container.setVisible(False)
        
        self._update_search_button()
    
    @Slot()
    def _update_search_button(self) -> None:
        """Actualiza el estado del botón de búsqueda."""
        selected_count = sum(1 for item in self._keyword_items if item.is_selected)
        self.search_btn.setEnabled(selected_count > 0)
        
        if selected_count > 0:
            self.search_btn.setText(f"🔍 Buscar Assets ({selected_count})")
        else:
            self.search_btn.setText("🔍 Buscar Assets")
    
    @Slot()
    def _on_search(self) -> None:
        """Emite la señal de búsqueda con las keywords seleccionadas."""
        selected = []
        for item in self._keyword_items:
            if item.is_selected:
                selected.append({
                    "keyword": item.keyword,
                    "timestamp": item.timestamp
                })
        
        if selected:
            self.search_requested.emit(selected)
    
    def get_selected_keywords(self) -> List[dict]:
        """Retorna las keywords seleccionadas."""
        return [
            {"keyword": item.keyword, "timestamp": item.timestamp}
            for item in self._keyword_items
            if item.is_selected
        ]
    
    def clear_keywords(self) -> None:
        """Limpia todas las keywords."""
        for item in self._keyword_items:
            item.deleteLater()
        self._keyword_items.clear()
        self.keywords_container.setVisible(False)
        self._update_search_button()


class ConceptSection(QFrame):
    """Sección de assets para un concepto específico."""
    
    def __init__(
        self,
        keyword: str,
        timestamp: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._keyword = keyword
        self._asset_cards: List[AssetCard] = []
        self._setup_ui(timestamp)
    
    def _setup_ui(self, timestamp: str) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #151520;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        keyword_label = QLabel(f"🔍 {self._keyword}")
        keyword_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        header_layout.addWidget(keyword_label)
        
        timestamp_label = QLabel(timestamp)
        timestamp_label.setStyleSheet("""
            QLabel {
                color: #6B7280;
                font-size: 12px;
                background-color: #1E1E2E;
                padding: 4px 8px;
                border-radius: 4px;
            }
        """)
        header_layout.addWidget(timestamp_label)
        
        header_layout.addStretch()
        
        # Botón de búsqueda manual
        search_btn = QPushButton("🔎 Buscar más")
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6366F1;
                border: 1px solid #6366F1;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.1);
            }
        """)
        header_layout.addWidget(search_btn)
        
        layout.addLayout(header_layout)
        
        # Scroll horizontal para assets
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedHeight(220)  # Altura fija para la galería
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                background-color: #1E1E2E;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4B5563;
                border-radius: 5px;
                min-width: 40px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #6366F1;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # Container de assets dentro del scroll
        assets_container = QWidget()
        assets_container.setStyleSheet("background-color: transparent;")
        self.assets_layout = QHBoxLayout(assets_container)
        self.assets_layout.setContentsMargins(0, 0, 0, 0)
        self.assets_layout.setSpacing(16)
        self.assets_layout.addStretch()
        
        scroll.setWidget(assets_container)
        layout.addWidget(scroll)
    
    # Señal para notificar cuando cambia la selección de un asset
    selection_changed = Signal(str, bool)  # asset_id, selected
    
    def add_asset(self, asset_id: str, source: str, asset_type: str, thumbnail_url: str = "") -> AssetCard:
        """Añade un asset a la sección."""
        card = AssetCard(asset_id, self._keyword, source, asset_type, thumbnail_url)
        self._asset_cards.append(card)
        # Insertar antes del stretch (último elemento)
        insert_pos = self.assets_layout.count() - 1
        self.assets_layout.insertWidget(insert_pos, card)
        # Reenviar señal de selección
        card.selection_changed.connect(self.selection_changed)
        return card
    
    def get_selected_assets(self) -> List[str]:
        """Retorna los IDs de los assets seleccionados."""
        return [card._asset_id for card in self._asset_cards if card.is_selected]


class PreviewPanel(QWidget):
    """Panel para preview y selección de assets."""
    
    assets_approved = Signal(list)  # Lista de asset IDs aprobados
    assets_selected = Signal(list)  # Lista de assets seleccionados (para timeline)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._concept_sections: List[ConceptSection] = []
        self._search_results: dict = {}  # Almacena StockAssets por keyword
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configura la interfaz del panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Título
        title = QLabel("🖼️ Preview de Assets")
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
            "Revisa los assets sugeridos para cada concepto. "
            "Haz clic en los que deseas incluir en tu timeline."
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
        
        # Sección de keywords manuales
        self.manual_keywords_section = ManualKeywordsSection()
        layout.addWidget(self.manual_keywords_section)
        
        # Stats bar
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border-radius: 8px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(16, 12, 16, 12)
        
        self.concepts_label = QLabel("0 conceptos")
        self.concepts_label.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        stats_layout.addWidget(self.concepts_label)
        
        stats_layout.addWidget(self._create_separator())
        
        self.assets_label = QLabel("0 assets encontrados")
        self.assets_label.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        stats_layout.addWidget(self.assets_label)
        
        stats_layout.addWidget(self._create_separator())
        
        self.selected_label = QLabel("0 seleccionados")
        self.selected_label.setStyleSheet("color: #6366F1; font-size: 13px; font-weight: 500;")
        stats_layout.addWidget(self.selected_label)
        
        stats_layout.addStretch()
        
        layout.addWidget(stats_frame)
        
        # Área de scroll para conceptos
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(16)
        
        # Mensaje de estado vacío
        self.empty_state = QFrame()
        self.empty_state.setMinimumHeight(300)
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignCenter)
        
        empty_icon = QLabel("🔍")
        empty_icon.setStyleSheet("font-size: 64px;")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_icon)
        
        empty_text = QLabel("No hay assets para mostrar")
        empty_text.setStyleSheet("""
            QLabel {
                color: #6B7280;
                font-size: 16px;
            }
        """)
        empty_text.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_text)
        
        empty_hint = QLabel("Primero transcribe un video y analiza los conceptos")
        empty_hint.setStyleSheet("""
            QLabel {
                color: #4B5563;
                font-size: 13px;
            }
        """)
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_hint)
        
        self.scroll_layout.addWidget(self.empty_state)
        self.scroll_layout.addStretch()
        
        scroll_area.setWidget(self.scroll_content)
        layout.addWidget(scroll_area, 1)
        
        # Botones de acción
        actions_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Seleccionar Todos")
        select_all_btn.setCursor(Qt.PointingHandCursor)
        select_all_btn.setStyleSheet("""
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
        select_all_btn.clicked.connect(self._on_select_all)
        actions_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deseleccionar Todos")
        deselect_all_btn.setCursor(Qt.PointingHandCursor)
        deselect_all_btn.setStyleSheet("""
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
        deselect_all_btn.clicked.connect(self._on_deselect_all)
        actions_layout.addWidget(deselect_all_btn)
        
        actions_layout.addStretch()
        
        # Botón para descargar assets seleccionados
        self.download_btn = QPushButton("⬇️ Descargar Assets")
        self.download_btn.setEnabled(False)
        self.download_btn.setMinimumHeight(44)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6B7280;
            }
        """)
        self.download_btn.clicked.connect(self._on_download)
        actions_layout.addWidget(self.download_btn)
        
        # Botón para exportar a DaVinci
        self.export_btn = QPushButton("🎬 Exportar a DaVinci")
        self.export_btn.setEnabled(False)
        self.export_btn.setMinimumHeight(44)
        self.export_btn.setMinimumWidth(180)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setStyleSheet("""
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
        self.export_btn.setToolTip(
            "Genera un script Python que se ejecuta\n"
            "dentro de DaVinci Resolve para importar\n"
            "los assets al timeline."
        )
        self.export_btn.clicked.connect(self._on_export_davinci)
        actions_layout.addWidget(self.export_btn)
        
        layout.addLayout(actions_layout)
    
    def _create_separator(self) -> QFrame:
        """Crea un separador vertical."""
        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #333344;")
        return separator
    
    def add_concept(self, keyword: str, timestamp: str) -> ConceptSection:
        """Añade un concepto con sus assets."""
        self.empty_state.setVisible(False)
        
        section = ConceptSection(keyword, timestamp)
        section.selection_changed.connect(self._on_selection_changed)
        self._concept_sections.append(section)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, section)
        
        self._update_stats()
        return section
    
    @Slot(str, bool)
    def _on_selection_changed(self, asset_id: str, selected: bool) -> None:
        """Actualiza estadísticas cuando cambia la selección de un asset."""
        self._update_stats()
    
    def clear_concepts(self) -> None:
        """Limpia todos los conceptos."""
        for section in self._concept_sections:
            section.deleteLater()
        self._concept_sections.clear()
        self.empty_state.setVisible(True)
        self._update_stats()
    
    def _update_stats(self) -> None:
        """Actualiza las estadísticas."""
        concept_count = len(self._concept_sections)
        asset_count = sum(len(s._asset_cards) for s in self._concept_sections)
        selected_count = sum(
            len(s.get_selected_assets()) 
            for s in self._concept_sections
        )
        
        self.concepts_label.setText(f"{concept_count} conceptos")
        self.assets_label.setText(f"{asset_count} assets encontrados")
        self.selected_label.setText(f"{selected_count} seleccionados")
        
        # Habilitar botones si hay selección
        has_selection = selected_count > 0
        self.download_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)
    
    @Slot()
    def _on_select_all(self) -> None:
        """Selecciona todos los assets."""
        for section in self._concept_sections:
            for card in section._asset_cards:
                card.set_selected(True)
        self._update_stats()
    
    @Slot()
    def _on_deselect_all(self) -> None:
        """Deselecciona todos los assets."""
        for section in self._concept_sections:
            for card in section._asset_cards:
                card.set_selected(False)
        self._update_stats()
    
    @Slot()
    def _on_download(self) -> None:
        """Descarga los assets seleccionados."""
        from PySide6.QtWidgets import QMessageBox, QFileDialog, QProgressDialog
        from PySide6.QtCore import Qt
        from pathlib import Path
        import httpx
        import re
        import unicodedata
        
        def sanitize_filename(name: str) -> str:
            """Limpia un nombre para usarlo como archivo."""
            # Normalizar unicode y remover acentos
            name = unicodedata.normalize('NFKD', name)
            name = name.encode('ascii', 'ignore').decode('ascii')
            # Remover caracteres no válidos
            name = re.sub(r'[^\w\s-]', '', name)
            # Reemplazar espacios con guiones bajos
            name = re.sub(r'[\s]+', '_', name)
            return name[:30] if name else 'asset'
        
        selected_ids = []
        for section in self._concept_sections:
            selected_ids.extend(section.get_selected_assets())
        
        if not selected_ids:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Por favor selecciona al menos un asset para descargar."
            )
            return
        
        # Obtener assets seleccionados con sus datos completos
        selected_assets = []
        
        for keyword, assets in self._search_results.items():
            for asset in assets:
                if asset.id in selected_ids:
                    download_url = getattr(asset, 'download_url', '') or getattr(asset, 'url', '')
                    if download_url:
                        selected_assets.append({
                            'id': asset.id,
                            'keyword': keyword,
                            'type': asset.type.value if hasattr(asset.type, 'value') else str(asset.type),
                            'download_url': download_url,
                        })
        
        if not selected_assets:
            QMessageBox.warning(
                self,
                "Error", 
                f"No se encontraron URLs de descarga.\n\n"
                f"IDs seleccionados: {len(selected_ids)}\n"
                f"IDs en resultados: {sum(len(a) for a in self._search_results.values())}"
            )
            return
        
        # Seleccionar carpeta de destino
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Carpeta de Descarga",
            "",
        )
        
        if not folder:
            return
        
        download_path = Path(folder)
        
        # Crear diálogo de progreso
        progress = QProgressDialog(
            "Descargando assets...",
            "Cancelar",
            0, len(selected_assets),
            self
        )
        progress.setWindowTitle("Descargando")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        
        downloaded = []
        errors = []
        
        for i, asset in enumerate(selected_assets):
            if progress.wasCanceled():
                break
            
            progress.setLabelText(f"Descargando {i+1}/{len(selected_assets)}...")
            progress.setValue(i)
            
            # Generar nombre de archivo único: índice + keyword + id
            ext = '.mp4' if asset['type'] == 'video' else '.jpg'
            safe_name = sanitize_filename(asset['keyword'])
            filename = f"{i+1:02d}_{safe_name}_{asset['id'][:8]}{ext}"
            filepath = download_path / filename
            
            try:
                # Descargar con httpx (síncrono para simplicidad)
                with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                    response = client.get(asset['download_url'])
                    response.raise_for_status()
                    
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    downloaded.append(filename)
                    
            except Exception as e:
                errors.append(f"{asset['keyword'][:20]}: {str(e)[:50]}")
        
        progress.setValue(len(selected_assets))
        progress.close()
        
        # Mostrar resultado
        if downloaded:
            msg = f"✅ Descargados {len(downloaded)} assets a:\n{download_path}\n\n"
            if errors:
                msg += f"⚠️ {len(errors)} errores:\n" + "\n".join(errors[:5])
            
            QMessageBox.information(self, "Descarga Completada", msg)
        else:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo descargar ningún asset.\n\nErrores:\n" + "\n".join(errors[:5])
            )
    
    @Slot()
    def _on_export_davinci(self) -> None:
        """Genera script de importación para DaVinci Resolve."""
        from PySide6.QtWidgets import QMessageBox, QFileDialog
        from pathlib import Path
        import re
        import unicodedata
        
        def sanitize_filename(name: str) -> str:
            """Limpia un nombre para usarlo como archivo."""
            name = unicodedata.normalize('NFKD', name)
            name = name.encode('ascii', 'ignore').decode('ascii')
            name = re.sub(r'[^\w\s-]', '', name)
            name = re.sub(r'[\s]+', '_', name)
            return name[:30] if name else 'asset'
        
        selected_ids = []
        for section in self._concept_sections:
            selected_ids.extend(section.get_selected_assets())
        
        if not selected_ids:
            QMessageBox.warning(
                self,
                "Sin selección",
                "Por favor selecciona al menos un asset para exportar."
            )
            return
        
        # Obtener assets seleccionados con sus datos completos
        selected_assets = []
        for keyword, assets in self._search_results.items():
            for asset in assets:
                if asset.id in selected_ids:
                    selected_assets.append({
                        'id': asset.id,
                        'keyword': keyword,
                        'source': asset.source,
                        'type': asset.type.value if hasattr(asset.type, 'value') else str(asset.type),
                        'download_url': getattr(asset, 'download_url', '') or getattr(asset, 'url', ''),
                        'thumbnail_url': getattr(asset, 'thumbnail_url', ''),
                    })
        
        if not selected_assets:
            QMessageBox.warning(
                self,
                "Error",
                "No se encontraron datos de los assets seleccionados."
            )
            return
        
        # Preguntar por la carpeta de descarga
        download_folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta donde están los assets descargados",
            ""
        )
        
        if not download_folder:
            return  # Usuario canceló
        
        download_path = Path(download_folder)
        
        try:
            # Generar script de DaVinci
            from src.davinci.script_generator import DaVinciScriptGenerator, ImportJob, BRollClip
            
            # Crear clips para el script (usando paths estimados)
            clips = []
            for i, asset in enumerate(selected_assets):
                # Nombre de archivo único (mismo formato que download)
                ext = '.mp4' if asset['type'] == 'video' else '.jpg'
                safe_name = sanitize_filename(asset['keyword'])
                filename = f"{i+1:02d}_{safe_name}_{asset['id'][:8]}{ext}"
                asset_path = download_path / filename
                
                clips.append(BRollClip(
                    asset_path=str(asset_path),
                    keyword=asset['keyword'],
                    start_time=i * 3.0,  # Placeholder: cada 3 segundos
                    end_time=(i + 1) * 3.0,
                    duration=3.0,
                    track_index=2
                ))
            
            job = ImportJob(
                project_name="Auto-B-Roll Project",
                clips=clips,
                target_track=2,
                frame_rate=24.0
            )
            
            generator = DaVinciScriptGenerator()
            
            # Generar y guardar script
            script_path = generator.generate_script(job, "auto_broll_import")
            
            # Copiar a carpeta de DaVinci
            installed_path = generator.install_script(script_path)
            
            # Crear archivo de URLs para descarga manual (temporal)
            urls_file = download_path / "assets_urls.txt"
            with open(urls_file, "w", encoding="utf-8") as f:
                f.write("# URLs de assets para descargar\n")
                f.write("# Descarga estos archivos y guarda con los nombres indicados\n\n")
                for asset in selected_assets:
                    ext = '.mp4' if asset['type'] == 'video' else '.jpg'
                    filename = f"{asset['keyword'][:30].replace(' ', '_')}_{asset['id'][:8]}{ext}"
                    f.write(f"{filename}\n")
                    f.write(f"  URL: {asset['download_url']}\n\n")
            
            QMessageBox.information(
                self,
                "✅ Script Generado",
                f"Script de DaVinci creado exitosamente.\n\n"
                f"📁 Script instalado en:\n{installed_path}\n\n"
                f"📝 Lista de URLs guardada en:\n{urls_file}\n\n"
                "Pasos siguientes:\n"
                "1. Descarga los assets usando las URLs del archivo\n"
                "2. Abre DaVinci Resolve\n"
                "3. Ve a Workspace → Scripts → Edit → Auto-B-Roll\n"
                "4. Ejecuta 'auto_broll_import'"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo generar el script:\n{e}"
            )
        
        # Emitir señal para procesar
        self.assets_approved.emit(selected_ids)
        self.assets_selected.emit(selected_ids)
    
    def load_demo_data(self) -> None:
        """Carga datos de demostración."""
        self.clear_concepts()
        
        # Concepto 1
        section1 = self.add_concept("inteligencia artificial", "00:15 - 00:22")
        section1.add_asset("pexels_1", "pexels", "video")
        section1.add_asset("pixabay_1", "pixabay", "video")
        section1.add_asset("unsplash_1", "unsplash", "image")
        
        # Concepto 2
        section2 = self.add_concept("video editing", "00:28 - 00:35")
        section2.add_asset("pexels_2", "pexels", "video")
        section2.add_asset("pexels_3", "pexels", "video")
        
        # Concepto 3
        section3 = self.add_concept("automation", "00:42 - 00:50")
        section3.add_asset("pixabay_2", "pixabay", "video")
        section3.add_asset("unsplash_2", "unsplash", "image")
        section3.add_asset("pexels_4", "pexels", "image")
        
        self._update_stats()
    
    def load_search_results(self, results: dict) -> None:
        """
        Carga los resultados de búsqueda en el panel.
        
        Args:
            results: Dict {keyword: [StockAsset, ...]}
        """
        self.clear_concepts()
        
        # Almacenar resultados completos para uso posterior
        self._search_results = results
        
        for keyword, assets in results.items():
            if not assets:
                continue  # Skip keywords sin resultados
            
            # Limpiar keyword (quitar comas al inicio)
            clean_keyword = keyword.strip().lstrip(',').strip()
            if not clean_keyword or len(clean_keyword) < 2:
                continue  # Skip keywords vacías o muy cortas
            
            section = self.add_concept(clean_keyword, "")
            
            for asset in assets[:5]:  # Máximo 5 assets por concepto
                # Obtener URL del thumbnail
                thumbnail_url = getattr(asset, 'preview_url', '') or getattr(asset, 'thumbnail_url', '') or ''
                
                section.add_asset(
                    asset.id,
                    asset.source,
                    asset.type.value if hasattr(asset.type, 'value') else str(asset.type),
                    thumbnail_url
                )
        
        self._update_stats()

