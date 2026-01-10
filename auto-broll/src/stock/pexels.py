"""
Cliente de Pexels API.

Implementación de la interfaz de stock para Pexels.
https://www.pexels.com/api/
"""

from typing import Optional, List
import os
import logging

import httpx

from .base import (
    StockAPI,
    StockAsset,
    SearchParams,
    SearchResult,
    AssetType,
    Orientation,
)

logger = logging.getLogger(__name__)


class PexelsAPI(StockAPI):
    """
    Cliente para Pexels API.
    
    Pexels ofrece fotos y videos gratuitos con atribución opcional.
    Rate limit: 200 requests/hora, 20,000 requests/mes.
    """
    
    BASE_URL = "https://api.pexels.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el cliente de Pexels.
        
        Args:
            api_key: API key de Pexels. Si es None, se busca en PEXELS_API_KEY
        """
        self._explicit_key = api_key  # Key explícita pasada al constructor
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def _api_key(self) -> Optional[str]:
        """Obtiene la API key (dinámicamente de env si no hay explícita)."""
        return self._explicit_key or os.getenv("PEXELS_API_KEY")
    
    @property
    def name(self) -> str:
        return "pexels"
    
    @property
    def supports_video(self) -> bool:
        return True
    
    @property
    def supports_images(self) -> bool:
        return True
    
    @property
    def requires_attribution(self) -> bool:
        return False  # Recomendado pero no requerido
    
    def is_configured(self) -> bool:
        return bool(self._api_key)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea el cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"Authorization": self._api_key},
                timeout=30.0,
            )
        return self._client
    
    async def close(self) -> None:
        """Cierra el cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def search(self, params: SearchParams) -> SearchResult:
        """Busca assets en Pexels."""
        if not self.is_configured():
            logger.warning("Pexels API no configurada")
            return SearchResult(
                query=params.query,
                source=self.name,
                total_results=0,
                page=params.page,
                per_page=params.per_page,
                assets=[],
            )
        
        assets = []
        
        # Buscar imágenes si aplica
        if params.type is None or params.type == AssetType.IMAGE:
            images = await self._search_photos(params)
            assets.extend(images)
        
        # Buscar videos si aplica
        if params.type is None or params.type == AssetType.VIDEO:
            videos = await self._search_videos(params)
            assets.extend(videos)
        
        # Limitar al número solicitado
        assets = assets[:params.per_page]
        
        return SearchResult(
            query=params.query,
            source=self.name,
            total_results=len(assets),
            page=params.page,
            per_page=params.per_page,
            assets=assets,
        )
    
    async def _search_photos(self, params: SearchParams) -> List[StockAsset]:
        """Busca fotos en Pexels."""
        client = await self._get_client()
        
        query_params = {
            "query": params.query,
            "per_page": params.per_page,
            "page": params.page,
            "locale": params.locale,
        }
        
        if params.orientation:
            query_params["orientation"] = params.orientation.value
        
        try:
            response = await client.get(
                f"{self.BASE_URL}/v1/search",
                params=query_params
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                self._parse_photo(photo, params.query)
                for photo in data.get("photos", [])
            ]
            
        except httpx.HTTPError as e:
            logger.error(f"Error buscando fotos en Pexels: {e}")
            return []
    
    async def _search_videos(self, params: SearchParams) -> List[StockAsset]:
        """Busca videos en Pexels."""
        client = await self._get_client()
        
        query_params = {
            "query": params.query,
            "per_page": params.per_page,
            "page": params.page,
        }
        
        if params.orientation:
            query_params["orientation"] = params.orientation.value
        
        try:
            response = await client.get(
                f"{self.BASE_URL}/videos/search",
                params=query_params
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                self._parse_video(video, params.query)
                for video in data.get("videos", [])
            ]
            
        except httpx.HTTPError as e:
            logger.error(f"Error buscando videos en Pexels: {e}")
            return []
    
    def _parse_photo(self, data: dict, query: str) -> StockAsset:
        """Parsea una foto de la respuesta de Pexels."""
        src = data.get("src", {})
        
        return StockAsset(
            id=f"pexels_photo_{data.get('id')}",
            source=self.name,
            type=AssetType.IMAGE,
            preview_url=src.get("medium", ""),
            download_url=src.get("original", src.get("large2x", "")),
            page_url=data.get("url", ""),
            width=data.get("width", 0),
            height=data.get("height", 0),
            title=data.get("alt", ""),
            photographer=data.get("photographer", ""),
            photographer_url=data.get("photographer_url", ""),
            search_query=query,
        )
    
    def _parse_video(self, data: dict, query: str) -> StockAsset:
        """Parsea un video de la respuesta de Pexels."""
        video_files = data.get("video_files", [])
        
        # Buscar el mejor archivo de video
        best_file = None
        for vf in video_files:
            if vf.get("quality") == "hd" and vf.get("width", 0) >= 1280:
                best_file = vf
                break
        
        if not best_file and video_files:
            best_file = video_files[0]
        
        download_url = best_file.get("link", "") if best_file else ""
        
        # Preview image
        video_pictures = data.get("video_pictures", [])
        preview_url = video_pictures[0].get("picture", "") if video_pictures else ""
        
        return StockAsset(
            id=f"pexels_video_{data.get('id')}",
            source=self.name,
            type=AssetType.VIDEO,
            preview_url=preview_url,
            download_url=download_url,
            page_url=data.get("url", ""),
            width=data.get("width", 0),
            height=data.get("height", 0),
            duration=data.get("duration"),
            photographer=data.get("user", {}).get("name", ""),
            photographer_url=data.get("user", {}).get("url", ""),
            search_query=query,
        )
    
    async def get_asset(self, asset_id: str) -> Optional[StockAsset]:
        """Obtiene un asset por ID."""
        if not self.is_configured():
            return None
        
        client = await self._get_client()
        
        # Determinar si es foto o video
        if "photo" in asset_id:
            numeric_id = asset_id.replace("pexels_photo_", "")
            endpoint = f"{self.BASE_URL}/v1/photos/{numeric_id}"
            parse_func = self._parse_photo
        elif "video" in asset_id:
            numeric_id = asset_id.replace("pexels_video_", "")
            endpoint = f"{self.BASE_URL}/videos/videos/{numeric_id}"
            parse_func = self._parse_video
        else:
            return None
        
        try:
            response = await client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            return parse_func(data, "")
            
        except httpx.HTTPError as e:
            logger.error(f"Error obteniendo asset de Pexels: {e}")
            return None
