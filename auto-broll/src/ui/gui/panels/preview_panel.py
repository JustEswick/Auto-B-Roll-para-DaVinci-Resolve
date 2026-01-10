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
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QPixmap


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


class AssetCard(QFrame):
    """Tarjeta de preview de un asset."""
    
    selection_changed = Signal(str, bool)  # id, selected
    
    def __init__(
        self,
        asset_id: str,
        keyword: str,
        source: str,
        asset_type: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._asset_id = asset_id
        self._selected = False
        self._setup_ui(keyword, source, asset_type)
    
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
        
        # Container con scroll horizontal para assets
        assets_container = QWidget()
        self.assets_layout = QHBoxLayout(assets_container)
        self.assets_layout.setContentsMargins(0, 0, 0, 0)
        self.assets_layout.setSpacing(16)  # Más espacio entre tarjetas
        self.assets_layout.addStretch()
        
        layout.addWidget(assets_container)
    
    def add_asset(self, asset_id: str, source: str, asset_type: str) -> AssetCard:
        """Añade un asset a la sección."""
        card = AssetCard(asset_id, self._keyword, source, asset_type)
        self._asset_cards.append(card)
        # Insertar antes del stretch (último elemento)
        insert_pos = self.assets_layout.count() - 1
        self.assets_layout.insertWidget(insert_pos, card)
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
        
        self.insert_btn = QPushButton("🎬 Insertar en Timeline")
        self.insert_btn.setEnabled(False)
        self.insert_btn.setMinimumHeight(44)
        self.insert_btn.setMinimumWidth(200)
        self.insert_btn.setCursor(Qt.PointingHandCursor)
        self.insert_btn.setStyleSheet("""
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
        self.insert_btn.clicked.connect(self._on_insert)
        actions_layout.addWidget(self.insert_btn)
        
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
        self._concept_sections.append(section)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, section)
        
        self._update_stats()
        return section
    
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
        
        self.insert_btn.setEnabled(selected_count > 0)
    
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
    def _on_insert(self) -> None:
        """Inserta los assets seleccionados en el timeline."""
        selected_ids = []
        for section in self._concept_sections:
            selected_ids.extend(section.get_selected_assets())
        
        if selected_ids:
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
        print(f"[DEBUG] PreviewPanel.load_search_results recibido: {len(results)} keywords")
        
        self.clear_concepts()
        
        for keyword, assets in results.items():
            if not assets:
                continue  # Skip keywords sin resultados
            
            # Limpiar keyword (quitar comas al inicio)
            clean_keyword = keyword.strip().lstrip(',').strip()
            if not clean_keyword or len(clean_keyword) < 2:
                continue  # Skip keywords vacías o muy cortas
            
            print(f"[DEBUG]   Agregando concepto '{clean_keyword}' con {len(assets)} assets")
            
            section = self.add_concept(clean_keyword, "")
            
            for asset in assets[:5]:  # Máximo 5 assets por concepto
                section.add_asset(
                    asset.id,
                    asset.source,
                    asset.type.value if hasattr(asset.type, 'value') else str(asset.type)
                )
        
        self._update_stats()
        print(f"[DEBUG] PreviewPanel: {len(self._concept_sections)} secciones cargadas")

