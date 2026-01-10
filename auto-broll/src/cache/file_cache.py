"""
Caché de Archivos.

Este módulo maneja el almacenamiento en caché de archivos
descargados (videos, imágenes, thumbnails).
"""

from typing import Optional, List, Dict
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class FileCache:
    """
    Gestor de caché de archivos en disco.
    
    Organiza y gestiona archivos descargados con:
    - Límite de tamaño configurable
    - Limpieza automática de archivos antiguos
    - Organización por categorías
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_size_mb: int = 500,
        max_age_days: int = 30
    ):
        """
        Inicializa el caché.
        
        Args:
            cache_dir: Directorio de caché
            max_size_mb: Tamaño máximo en MB
            max_age_days: Edad máxima de archivos en días
        """
        if cache_dir is None:
            from ..config import CACHE_DIR
            cache_dir = CACHE_DIR
        
        self._cache_dir = Path(cache_dir)
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._max_age = timedelta(days=max_age_days)
        
        # Subdirectorios
        self._videos_dir = self._cache_dir / "videos"
        self._images_dir = self._cache_dir / "images"
        self._thumbnails_dir = self._cache_dir / "thumbnails"
        
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Crea los directorios necesarios."""
        for directory in [
            self._cache_dir,
            self._videos_dir,
            self._images_dir,
            self._thumbnails_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def videos_dir(self) -> Path:
        """Directorio de videos."""
        return self._videos_dir
    
    @property
    def images_dir(self) -> Path:
        """Directorio de imágenes."""
        return self._images_dir
    
    @property
    def thumbnails_dir(self) -> Path:
        """Directorio de thumbnails."""
        return self._thumbnails_dir
    
    # =========================================================================
    # Gestión de Archivos
    # =========================================================================
    
    def get_file_path(
        self,
        asset_id: str,
        asset_type: str,
        extension: str = ""
    ) -> Path:
        """
        Genera la ruta para un archivo de asset.
        
        Args:
            asset_id: ID del asset
            asset_type: 'video', 'image' o 'thumbnail'
            extension: Extensión del archivo
            
        Returns:
            Ruta del archivo
        """
        # Sanitizar el asset_id para usarlo como nombre de archivo
        safe_id = self._sanitize_filename(asset_id)
        
        if asset_type == "video":
            directory = self._videos_dir
            ext = extension or ".mp4"
        elif asset_type == "thumbnail":
            directory = self._thumbnails_dir
            ext = extension or ".jpg"
        else:
            directory = self._images_dir
            ext = extension or ".jpg"
        
        return directory / f"{safe_id}{ext}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitiza un nombre de archivo."""
        # Reemplazar caracteres no válidos
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename[:100]  # Limitar longitud
    
    def file_exists(self, asset_id: str, asset_type: str) -> bool:
        """Verifica si un archivo existe en caché."""
        path = self.get_file_path(asset_id, asset_type)
        return path.exists()
    
    def get_cached_file(
        self,
        asset_id: str,
        asset_type: str
    ) -> Optional[Path]:
        """
        Obtiene un archivo del caché si existe.
        
        Args:
            asset_id: ID del asset
            asset_type: Tipo de asset
            
        Returns:
            Ruta del archivo o None
        """
        path = self.get_file_path(asset_id, asset_type)
        
        if path.exists():
            # Actualizar tiempo de acceso
            path.touch()
            return path
        
        return None
    
    def save_file(
        self,
        asset_id: str,
        asset_type: str,
        content: bytes,
        extension: str = ""
    ) -> Path:
        """
        Guarda contenido en el caché.
        
        Args:
            asset_id: ID del asset
            asset_type: Tipo de asset
            content: Contenido del archivo
            extension: Extensión del archivo
            
        Returns:
            Ruta del archivo guardado
        """
        path = self.get_file_path(asset_id, asset_type, extension)
        
        with open(path, 'wb') as f:
            f.write(content)
        
        logger.debug(f"Archivo guardado en caché: {path.name}")
        return path
    
    def copy_to_cache(
        self,
        source_path: Path,
        asset_id: str,
        asset_type: str
    ) -> Path:
        """
        Copia un archivo existente al caché.
        
        Args:
            source_path: Ruta del archivo origen
            asset_id: ID del asset
            asset_type: Tipo de asset
            
        Returns:
            Ruta del archivo en caché
        """
        extension = source_path.suffix
        dest_path = self.get_file_path(asset_id, asset_type, extension)
        
        shutil.copy2(source_path, dest_path)
        logger.debug(f"Archivo copiado a caché: {dest_path.name}")
        
        return dest_path
    
    def delete_file(self, asset_id: str, asset_type: str) -> bool:
        """Elimina un archivo del caché."""
        path = self.get_file_path(asset_id, asset_type)
        
        if path.exists():
            path.unlink()
            logger.debug(f"Archivo eliminado del caché: {path.name}")
            return True
        
        return False
    
    # =========================================================================
    # Estadísticas y Limpieza
    # =========================================================================
    
    def get_cache_size(self) -> int:
        """Obtiene el tamaño total del caché en bytes."""
        total = 0
        
        for directory in [self._videos_dir, self._images_dir, self._thumbnails_dir]:
            for file in directory.iterdir():
                if file.is_file():
                    total += file.stat().st_size
        
        return total
    
    def get_cache_size_mb(self) -> float:
        """Obtiene el tamaño total del caché en MB."""
        return self.get_cache_size() / (1024 * 1024)
    
    def get_file_count(self) -> Dict[str, int]:
        """Obtiene el conteo de archivos por tipo."""
        return {
            "videos": sum(1 for _ in self._videos_dir.iterdir() if _.is_file()),
            "images": sum(1 for _ in self._images_dir.iterdir() if _.is_file()),
            "thumbnails": sum(1 for _ in self._thumbnails_dir.iterdir() if _.is_file()),
        }
    
    def get_stats(self) -> Dict[str, any]:
        """Obtiene estadísticas del caché."""
        counts = self.get_file_count()
        size_mb = self.get_cache_size_mb()
        
        return {
            "size_mb": round(size_mb, 2),
            "max_size_mb": self._max_size_bytes / (1024 * 1024),
            "usage_percent": round((size_mb / (self._max_size_bytes / (1024 * 1024))) * 100, 1),
            **counts,
            "total_files": sum(counts.values()),
        }
    
    def cleanup_old_files(self) -> int:
        """
        Elimina archivos más antiguos que max_age.
        
        Returns:
            Número de archivos eliminados
        """
        cutoff = datetime.now() - self._max_age
        deleted = 0
        
        for directory in [self._videos_dir, self._images_dir, self._thumbnails_dir]:
            for file in directory.iterdir():
                if file.is_file():
                    mtime = datetime.fromtimestamp(file.stat().st_mtime)
                    if mtime < cutoff:
                        file.unlink()
                        deleted += 1
        
        if deleted > 0:
            logger.info(f"Limpieza de caché: {deleted} archivos antiguos eliminados")
        
        return deleted
    
    def cleanup_if_needed(self) -> int:
        """
        Limpia el caché si excede el tamaño máximo.
        
        Elimina los archivos menos usados (más antiguos por mtime).
        
        Returns:
            Número de archivos eliminados
        """
        current_size = self.get_cache_size()
        
        if current_size <= self._max_size_bytes:
            return 0
        
        # Obtener todos los archivos ordenados por tiempo de acceso
        all_files = []
        for directory in [self._videos_dir, self._images_dir, self._thumbnails_dir]:
            for file in directory.iterdir():
                if file.is_file():
                    all_files.append((file, file.stat().st_mtime, file.stat().st_size))
        
        # Ordenar por tiempo de acceso (más antiguo primero)
        all_files.sort(key=lambda x: x[1])
        
        deleted = 0
        freed = 0
        target_size = int(self._max_size_bytes * 0.8)  # Reducir al 80%
        
        for file_path, _, file_size in all_files:
            if current_size - freed <= target_size:
                break
            
            file_path.unlink()
            freed += file_size
            deleted += 1
        
        if deleted > 0:
            logger.info(
                f"Limpieza de caché: {deleted} archivos eliminados, "
                f"{freed / (1024 * 1024):.1f} MB liberados"
            )
        
        return deleted
    
    def clear_all(self) -> int:
        """
        Elimina todos los archivos del caché.
        
        Returns:
            Número de archivos eliminados
        """
        deleted = 0
        
        for directory in [self._videos_dir, self._images_dir, self._thumbnails_dir]:
            for file in directory.iterdir():
                if file.is_file():
                    file.unlink()
                    deleted += 1
        
        logger.info(f"Caché limpiado completamente: {deleted} archivos eliminados")
        return deleted
