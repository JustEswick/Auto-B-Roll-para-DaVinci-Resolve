"""
Gestor de Media Pool de DaVinci Resolve.

Este módulo proporciona funciones para gestionar el Media Pool:
importar archivos, organizar en carpetas, etc.
"""

from typing import Optional, List, Any
from pathlib import Path
import logging

from .resolve_api import ResolveAPI

logger = logging.getLogger(__name__)


class MediaPoolManager:
    """
    Gestor del Media Pool de DaVinci Resolve.
    
    Proporciona métodos para importar y organizar medios
    en el Media Pool.
    """
    
    # Nombre de la carpeta para B-Roll importado
    BROLL_FOLDER_NAME = "Auto-B-Roll Assets"
    
    def __init__(self, resolve_api: ResolveAPI):
        """
        Inicializa el gestor.
        
        Args:
            resolve_api: Instancia de ResolveAPI conectada
        """
        self._api = resolve_api
        self._broll_folder: Optional[Any] = None
    
    @property
    def media_pool(self) -> Optional[Any]:
        """Retorna el Media Pool."""
        return self._api.media_pool
    
    def _ensure_connected(self) -> bool:
        """Verifica que hay conexión con Resolve."""
        if not self._api.is_connected:
            logger.error("No hay conexión con DaVinci Resolve")
            return False
        if not self.media_pool:
            logger.error("No se pudo acceder al Media Pool")
            return False
        return True
    
    # =========================================================================
    # Carpetas
    # =========================================================================
    
    def get_or_create_broll_folder(self) -> Optional[Any]:
        """
        Obtiene o crea la carpeta para assets de B-Roll.
        
        Returns:
            Carpeta de B-Roll o None
        """
        if self._broll_folder:
            return self._broll_folder
        
        if not self._ensure_connected():
            return None
        
        root = self.media_pool.GetRootFolder()
        if not root:
            return None
        
        # Buscar carpeta existente
        subfolders = root.GetSubFolderList()
        if subfolders:
            for folder in subfolders:
                if folder.GetName() == self.BROLL_FOLDER_NAME:
                    self._broll_folder = folder
                    logger.info(f"Carpeta B-Roll encontrada: {self.BROLL_FOLDER_NAME}")
                    return self._broll_folder
        
        # Crear nueva carpeta
        self.media_pool.SetCurrentFolder(root)
        self._broll_folder = self.media_pool.AddSubFolder(root, self.BROLL_FOLDER_NAME)
        
        if self._broll_folder:
            logger.info(f"Carpeta B-Roll creada: {self.BROLL_FOLDER_NAME}")
        else:
            logger.error("No se pudo crear la carpeta de B-Roll")
        
        return self._broll_folder
    
    def get_folder_contents(self, folder: Optional[Any] = None) -> List[Any]:
        """
        Obtiene el contenido de una carpeta.
        
        Args:
            folder: Carpeta a listar (None = carpeta actual)
            
        Returns:
            Lista de items en la carpeta
        """
        if not self._ensure_connected():
            return []
        
        if folder is None:
            folder = self.media_pool.GetCurrentFolder()
        
        if not folder:
            return []
        
        return folder.GetClipList() or []
    
    # =========================================================================
    # Importación
    # =========================================================================
    
    def import_files(
        self,
        file_paths: List[Path],
        to_broll_folder: bool = True
    ) -> List[Any]:
        """
        Importa archivos al Media Pool.
        
        Args:
            file_paths: Lista de rutas de archivos
            to_broll_folder: Si True, importa a la carpeta de B-Roll
            
        Returns:
            Lista de clips importados
        """
        if not self._ensure_connected():
            return []
        
        if not file_paths:
            return []
        
        # Convertir a strings
        path_strings = [str(p) for p in file_paths if p.exists()]
        
        if not path_strings:
            logger.warning("No hay archivos válidos para importar")
            return []
        
        # Cambiar a carpeta de B-Roll si es necesario
        if to_broll_folder:
            broll_folder = self.get_or_create_broll_folder()
            if broll_folder:
                self.media_pool.SetCurrentFolder(broll_folder)
        
        # Importar
        try:
            clips = self.media_pool.ImportMedia(path_strings)
            
            if clips:
                logger.info(f"Importados {len(clips)} archivos al Media Pool")
                return list(clips) if clips else []
            else:
                logger.warning("No se importaron archivos")
                return []
                
        except Exception as e:
            logger.error(f"Error al importar archivos: {e}")
            return []
    
    def import_file(self, file_path: Path, to_broll_folder: bool = True) -> Optional[Any]:
        """
        Importa un solo archivo.
        
        Args:
            file_path: Ruta del archivo
            to_broll_folder: Si True, importa a la carpeta de B-Roll
            
        Returns:
            Clip importado o None
        """
        clips = self.import_files([file_path], to_broll_folder)
        return clips[0] if clips else None
    
    # =========================================================================
    # Búsqueda
    # =========================================================================
    
    def find_clip_by_name(self, name: str, folder: Optional[Any] = None) -> Optional[Any]:
        """
        Busca un clip por nombre.
        
        Args:
            name: Nombre del clip (parcial o completo)
            folder: Carpeta donde buscar (None = raíz)
            
        Returns:
            Clip encontrado o None
        """
        if not self._ensure_connected():
            return None
        
        if folder is None:
            folder = self.media_pool.GetRootFolder()
        
        clips = self.get_folder_contents(folder)
        
        for clip in clips:
            clip_name = clip.GetName()
            if name.lower() in clip_name.lower():
                return clip
        
        return None
    
    def get_clip_info(self, clip: Any) -> dict:
        """
        Obtiene información de un clip.
        
        Args:
            clip: Clip del Media Pool
            
        Returns:
            Diccionario con información del clip
        """
        if not clip:
            return {}
        
        try:
            return {
                "name": clip.GetName(),
                "duration": clip.GetClipProperty("Duration"),
                "fps": clip.GetClipProperty("FPS"),
                "resolution": f"{clip.GetClipProperty('Resolution')}",
                "file_path": clip.GetClipProperty("File Path"),
                "type": clip.GetClipProperty("Type"),
            }
        except Exception as e:
            logger.error(f"Error obteniendo info del clip: {e}")
            return {"name": clip.GetName() if clip else "Unknown"}
    
    # =========================================================================
    # Limpieza
    # =========================================================================
    
    def clear_broll_folder(self) -> bool:
        """
        Limpia la carpeta de B-Roll.
        
        Returns:
            True si fue exitoso
        """
        if not self._ensure_connected():
            return False
        
        broll_folder = self.get_or_create_broll_folder()
        if not broll_folder:
            return False
        
        clips = broll_folder.GetClipList()
        if not clips:
            return True
        
        try:
            for clip in clips:
                self.media_pool.DeleteClips([clip])
            
            logger.info(f"Carpeta B-Roll limpiada ({len(clips)} clips eliminados)")
            return True
            
        except Exception as e:
            logger.error(f"Error al limpiar carpeta B-Roll: {e}")
            return False
