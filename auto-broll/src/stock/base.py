"""
Base para APIs de Stock.

Define la interfaz abstracta para todas las APIs de stock
y las estructuras de datos comunes.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum


class AssetType(Enum):
    """Tipos de assets."""
    IMAGE = "image"
    VIDEO = "video"


class Orientation(Enum):
    """Orientaciones de assets."""
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    SQUARE = "square"


@dataclass
class StockAsset:
    """
    Representa un asset de stock.
    
    Estructura unificada para assets de cualquier API.
    """
    id: str
    source: str  # pexels, pixabay, unsplash
    type: AssetType
    
    # URLs
    preview_url: str  # URL de preview/thumbnail
    download_url: str  # URL de descarga (mejor calidad)
    page_url: str  # URL de la página del asset
    
    # Metadatos
    width: int = 0
    height: int = 0
    duration: Optional[float] = None  # Solo para videos
    
    # Información adicional
    title: str = ""
    description: str = ""
    photographer: str = ""
    photographer_url: str = ""
    
    # Búsqueda
    search_query: str = ""
    relevance_score: float = 1.0
    
    # Estado local
    local_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    downloaded: bool = False
    
    @property
    def orientation(self) -> Orientation:
        """Determina la orientación del asset."""
        if self.width == 0 or self.height == 0:
            return Orientation.LANDSCAPE
        
        ratio = self.width / self.height
        
        if ratio > 1.2:
            return Orientation.LANDSCAPE
        elif ratio < 0.8:
            return Orientation.PORTRAIT
        else:
            return Orientation.SQUARE
    
    @property
    def aspect_ratio(self) -> str:
        """Retorna el aspect ratio aproximado."""
        if self.width == 0 or self.height == 0:
            return "16:9"
        
        ratio = self.width / self.height
        
        if 1.7 < ratio < 1.8:
            return "16:9"
        elif 1.3 < ratio < 1.4:
            return "4:3"
        elif 0.55 < ratio < 0.58:
            return "9:16"
        elif 0.9 < ratio < 1.1:
            return "1:1"
        else:
            return f"{self.width}:{self.height}"


@dataclass
class SearchParams:
    """Parámetros de búsqueda para APIs de stock."""
    query: str
    type: Optional[AssetType] = None  # None = ambos
    orientation: Optional[Orientation] = None
    min_width: int = 0
    min_height: int = 0
    per_page: int = 10
    page: int = 1
    locale: str = "es-ES"


@dataclass
class SearchResult:
    """Resultado de una búsqueda."""
    query: str
    source: str
    total_results: int
    page: int
    per_page: int
    assets: List[StockAsset] = field(default_factory=list)
    
    @property
    def has_more(self) -> bool:
        """Indica si hay más resultados disponibles."""
        return len(self.assets) == self.per_page


class StockAPI(ABC):
    """
    Interfaz abstracta para APIs de stock.
    
    Todas las implementaciones de APIs de stock deben heredar
    de esta clase e implementar sus métodos abstractos.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre de la API."""
        pass
    
    @property
    @abstractmethod
    def supports_video(self) -> bool:
        """Indica si la API soporta videos."""
        pass
    
    @property
    @abstractmethod
    def supports_images(self) -> bool:
        """Indica si la API soporta imágenes."""
        pass
    
    @property
    @abstractmethod
    def requires_attribution(self) -> bool:
        """Indica si se requiere atribución."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Verifica si la API está configurada (tiene API key)."""
        pass
    
    @abstractmethod
    async def search(self, params: SearchParams) -> SearchResult:
        """
        Busca assets según los parámetros.
        
        Args:
            params: Parámetros de búsqueda
            
        Returns:
            Resultado con los assets encontrados
        """
        pass
    
    @abstractmethod
    async def get_asset(self, asset_id: str) -> Optional[StockAsset]:
        """
        Obtiene un asset específico por ID.
        
        Args:
            asset_id: ID del asset
            
        Returns:
            Asset encontrado o None
        """
        pass
    
    async def search_images(
        self,
        query: str,
        per_page: int = 10
    ) -> SearchResult:
        """Busca solo imágenes."""
        return await self.search(SearchParams(
            query=query,
            type=AssetType.IMAGE,
            per_page=per_page
        ))
    
    async def search_videos(
        self,
        query: str,
        per_page: int = 10
    ) -> SearchResult:
        """Busca solo videos."""
        return await self.search(SearchParams(
            query=query,
            type=AssetType.VIDEO,
            per_page=per_page
        ))
