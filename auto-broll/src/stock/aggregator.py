"""
Agregador de APIs de Stock.

Combina resultados de múltiples APIs de stock y los ordena
por relevancia.
"""

from typing import Optional, List, Dict
import asyncio
import logging

from .base import StockAPI, StockAsset, SearchParams, SearchResult, AssetType
from .pexels import PexelsAPI

logger = logging.getLogger(__name__)


class StockAggregator:
    """
    Agregador de múltiples APIs de stock.
    
    Permite buscar en todas las APIs configuradas simultáneamente
    y combinar los resultados de forma ordenada.
    """
    
    def __init__(self):
        """Inicializa el agregador con las APIs disponibles."""
        self._apis: Dict[str, StockAPI] = {}
        self._init_apis()
    
    def _init_apis(self) -> None:
        """Inicializa las APIs disponibles (verifica configuración actual)."""
        self._apis.clear()
        
        # Pexels
        pexels = PexelsAPI()
        if pexels.is_configured():
            self._apis["pexels"] = pexels
            logger.info("Pexels API configurada")
        
        # TODO: Agregar Pixabay y Unsplash cuando se implementen
        # pixabay = PixabayAPI()
        # if pixabay.is_configured():
        #     self._apis["pixabay"] = pixabay
        
        # unsplash = UnsplashAPI()
        # if unsplash.is_configured():
        #     self._apis["unsplash"] = unsplash
    
    def refresh_apis(self) -> None:
        """Refresca las APIs disponibles (útil después de cambiar config)."""
        self._init_apis()
    
    @property
    def available_apis(self) -> List[str]:
        """Retorna las APIs disponibles y configuradas."""
        return list(self._apis.keys())
    
    @property
    def api_count(self) -> int:
        """Retorna el número de APIs configuradas."""
        return len(self._apis)
    
    def is_any_configured(self) -> bool:
        """Verifica si al menos una API está configurada."""
        # Reinicializar para detectar cambios en config
        self._init_apis()
        return len(self._apis) > 0
    
    async def search(
        self,
        query: str,
        asset_type: Optional[AssetType] = None,
        per_api: int = 10,
        apis: Optional[List[str]] = None
    ) -> List[StockAsset]:
        """
        Busca assets en todas las APIs configuradas.
        
        Args:
            query: Término de búsqueda
            asset_type: Tipo de asset (imagen/video/ambos)
            per_api: Resultados por cada API
            apis: Lista de APIs a usar. None = todas
            
        Returns:
            Lista combinada y ordenada de assets
        """
        if not self.is_any_configured():
            logger.warning("No hay APIs de stock configuradas")
            return []
        
        # Determinar qué APIs usar
        apis_to_search = self._apis
        if apis:
            apis_to_search = {
                name: api 
                for name, api in self._apis.items() 
                if name in apis
            }
        
        # Crear parámetros de búsqueda
        params = SearchParams(
            query=query,
            type=asset_type,
            per_page=per_api,
        )
        
        # Buscar en paralelo en todas las APIs
        tasks = [
            api.search(params)
            for api in apis_to_search.values()
        ]
        
        try:
            results: List[SearchResult] = await asyncio.gather(
                *tasks,
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"Error en búsqueda paralela: {e}")
            return []
        
        # Combinar resultados
        all_assets: List[StockAsset] = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Una API falló: {result}")
                continue
            
            if isinstance(result, SearchResult):
                all_assets.extend(result.assets)
        
        # Ordenar por relevancia y diversificar fuentes
        sorted_assets = self._rank_and_diversify(all_assets)
        
        logger.info(
            f"Búsqueda '{query}': {len(sorted_assets)} assets de "
            f"{len(apis_to_search)} APIs"
        )
        
        return sorted_assets
    
    def _rank_and_diversify(self, assets: List[StockAsset]) -> List[StockAsset]:
        """
        Ordena y diversifica los resultados.
        
        Alterna entre diferentes fuentes para evitar que una
        sola API domine los resultados.
        """
        if not assets:
            return []
        
        # Agrupar por fuente
        by_source: Dict[str, List[StockAsset]] = {}
        for asset in assets:
            if asset.source not in by_source:
                by_source[asset.source] = []
            by_source[asset.source].append(asset)
        
        # Intercalar resultados de diferentes fuentes
        result = []
        sources = list(by_source.keys())
        max_per_source = max(len(items) for items in by_source.values())
        
        for i in range(max_per_source):
            for source in sources:
                if i < len(by_source[source]):
                    result.append(by_source[source][i])
        
        return result
    
    async def search_for_keywords(
        self,
        keywords: List[str],
        asset_type: Optional[AssetType] = None,
        per_keyword: int = 3
    ) -> Dict[str, List[StockAsset]]:
        """
        Busca assets para múltiples keywords.
        
        Args:
            keywords: Lista de palabras clave
            asset_type: Tipo de asset
            per_keyword: Resultados por keyword
            
        Returns:
            Diccionario {keyword: [assets]}
        """
        results: Dict[str, List[StockAsset]] = {}
        
        # Buscar en paralelo todas las keywords
        tasks = [
            self.search(keyword, asset_type, per_keyword)
            for keyword in keywords
        ]
        
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for keyword, assets in zip(keywords, search_results):
            if isinstance(assets, Exception):
                logger.warning(f"Error buscando '{keyword}': {assets}")
                results[keyword] = []
            else:
                results[keyword] = assets
        
        return results
    
    async def close(self) -> None:
        """Cierra todas las conexiones de APIs."""
        for api in self._apis.values():
            if hasattr(api, 'close'):
                await api.close()
