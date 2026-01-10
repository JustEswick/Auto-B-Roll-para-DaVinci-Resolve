"""
Descargador de Assets.

Maneja la descarga asíncrona de assets desde las APIs de stock.
"""

from typing import Optional, List, Callable
from pathlib import Path
import asyncio
import aiohttp
import logging
from dataclasses import dataclass

from .base import StockAsset

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Resultado de una descarga."""
    asset_id: str
    success: bool
    local_path: Optional[Path] = None
    error: Optional[str] = None
    file_size: int = 0


class AssetDownloader:
    """
    Descargador asíncrono de assets.
    
    Maneja descargas paralelas con límite de concurrencia
    y reporta progreso.
    """
    
    def __init__(
        self,
        download_dir: Path,
        max_concurrent: int = 5,
        timeout: int = 60
    ):
        """
        Inicializa el descargador.
        
        Args:
            download_dir: Directorio para guardar descargas
            max_concurrent: Número máximo de descargas simultáneas
            timeout: Timeout por descarga en segundos
        """
        self._download_dir = Path(download_dir)
        self._download_dir.mkdir(parents=True, exist_ok=True)
        
        self._max_concurrent = max_concurrent
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def download(
        self,
        asset: StockAsset,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> DownloadResult:
        """
        Descarga un asset individual.
        
        Args:
            asset: Asset a descargar
            progress_callback: Callback de progreso (0.0 - 1.0)
            
        Returns:
            Resultado de la descarga
        """
        async with self._semaphore:
            return await self._download_single(asset, progress_callback)
    
    async def _download_single(
        self,
        asset: StockAsset,
        progress_callback: Optional[Callable[[float], None]]
    ) -> DownloadResult:
        """Descarga un solo asset."""
        if not asset.download_url:
            return DownloadResult(
                asset_id=asset.id,
                success=False,
                error="URL de descarga no disponible"
            )
        
        # Determinar nombre de archivo
        ext = self._get_extension(asset)
        filename = f"{asset.id}{ext}"
        local_path = self._download_dir / filename
        
        # Si ya existe, retornar
        if local_path.exists():
            logger.debug(f"Asset ya descargado: {filename}")
            return DownloadResult(
                asset_id=asset.id,
                success=True,
                local_path=local_path,
                file_size=local_path.stat().st_size
            )
        
        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(asset.download_url) as response:
                    if response.status != 200:
                        return DownloadResult(
                            asset_id=asset.id,
                            success=False,
                            error=f"HTTP {response.status}"
                        )
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(local_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded / total_size)
            
            logger.info(f"Descargado: {filename} ({downloaded / 1024:.1f} KB)")
            
            return DownloadResult(
                asset_id=asset.id,
                success=True,
                local_path=local_path,
                file_size=downloaded
            )
            
        except asyncio.TimeoutError:
            return DownloadResult(
                asset_id=asset.id,
                success=False,
                error="Timeout"
            )
        except aiohttp.ClientError as e:
            return DownloadResult(
                asset_id=asset.id,
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Error descargando {asset.id}: {e}")
            return DownloadResult(
                asset_id=asset.id,
                success=False,
                error=str(e)
            )
    
    async def download_many(
        self,
        assets: List[StockAsset],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[DownloadResult]:
        """
        Descarga múltiples assets en paralelo.
        
        Args:
            assets: Lista de assets a descargar
            progress_callback: Callback (completados, total)
            
        Returns:
            Lista de resultados
        """
        if not assets:
            return []
        
        completed = 0
        results: List[DownloadResult] = []
        
        async def download_with_progress(asset: StockAsset) -> DownloadResult:
            nonlocal completed
            result = await self.download(asset)
            completed += 1
            
            if progress_callback:
                progress_callback(completed, len(assets))
            
            return result
        
        tasks = [download_with_progress(asset) for asset in assets]
        results = await asyncio.gather(*tasks)
        
        # Estadísticas
        successful = sum(1 for r in results if r.success)
        total_size = sum(r.file_size for r in results if r.success)
        
        logger.info(
            f"Descarga completada: {successful}/{len(assets)} exitosas, "
            f"{total_size / 1024 / 1024:.1f} MB total"
        )
        
        return results
    
    def _get_extension(self, asset: StockAsset) -> str:
        """Determina la extensión del archivo."""
        from .base import AssetType
        
        if asset.type == AssetType.VIDEO:
            return ".mp4"
        else:
            # Intentar extraer de la URL
            url = asset.download_url.lower()
            for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                if ext in url:
                    return ext
            return ".jpg"
    
    def get_cached_path(self, asset_id: str) -> Optional[Path]:
        """
        Verifica si un asset está en caché.
        
        Args:
            asset_id: ID del asset
            
        Returns:
            Path si existe, None si no
        """
        for ext in [".mp4", ".jpg", ".jpeg", ".png", ".webp"]:
            path = self._download_dir / f"{asset_id}{ext}"
            if path.exists():
                return path
        return None
    
    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """
        Limpia el caché de descargas.
        
        Args:
            older_than_days: Solo eliminar archivos más antiguos que X días.
                           None = eliminar todo.
                           
        Returns:
            Número de archivos eliminados
        """
        import time
        
        deleted = 0
        now = time.time()
        max_age = (older_than_days or 0) * 24 * 60 * 60
        
        for file in self._download_dir.iterdir():
            if file.is_file():
                if older_than_days is None:
                    file.unlink()
                    deleted += 1
                else:
                    age = now - file.stat().st_mtime
                    if age > max_age:
                        file.unlink()
                        deleted += 1
        
        logger.info(f"Cache limpiado: {deleted} archivos eliminados")
        return deleted
