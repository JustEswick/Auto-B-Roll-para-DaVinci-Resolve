"""
API de DaVinci Resolve.

Este módulo proporciona la interfaz para comunicarse con
DaVinci Resolve a través de su Scripting API.
"""

from typing import Optional, Any, List
from pathlib import Path
import sys
import logging

logger = logging.getLogger(__name__)


class ResolveConnectionError(Exception):
    """Error de conexión con DaVinci Resolve."""
    pass


class ResolveAPI:
    """
    Interfaz con DaVinci Resolve Scripting API.
    
    Proporciona métodos de alto nivel para interactuar con
    DaVinci Resolve: proyectos, timelines, media pool, etc.
    
    Requiere que DaVinci Resolve esté ejecutándose con un
    proyecto abierto.
    """
    
    # Paths donde puede estar el módulo de Resolve
    RESOLVE_SCRIPT_PATHS = [
        # Windows
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules",
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules",
        # macOS
        "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
        # Linux
        "/opt/resolve/Developer/Scripting/Modules",
    ]
    
    def __init__(self):
        """Inicializa la conexión con DaVinci Resolve."""
        self._resolve = None
        self._project_manager = None
        self._current_project = None
        self._media_pool = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        Conecta con DaVinci Resolve.
        
        Returns:
            True si la conexión fue exitosa
            
        Raises:
            ResolveConnectionError: Si no se puede conectar
        """
        if self._connected:
            return True
        
        # Agregar paths del módulo de Resolve
        self._add_resolve_paths()
        
        try:
            # Importar el módulo de Resolve
            import DaVinciResolveScript as dvr
            
            # Obtener instancia de Resolve
            self._resolve = dvr.scriptapp("Resolve")
            
            if self._resolve is None:
                raise ResolveConnectionError(
                    "DaVinci Resolve no está ejecutándose.\n"
                    "Por favor, abre DaVinci Resolve con un proyecto activo."
                )
            
            # Obtener project manager
            self._project_manager = self._resolve.GetProjectManager()
            
            if self._project_manager is None:
                raise ResolveConnectionError(
                    "No se pudo obtener el Project Manager."
                )
            
            # Obtener proyecto actual
            self._current_project = self._project_manager.GetCurrentProject()
            
            if self._current_project is None:
                raise ResolveConnectionError(
                    "No hay un proyecto abierto en DaVinci Resolve.\n"
                    "Por favor, abre o crea un proyecto."
                )
            
            # Obtener Media Pool
            self._media_pool = self._current_project.GetMediaPool()
            
            self._connected = True
            
            project_name = self._current_project.GetName()
            logger.info(f"Conectado a DaVinci Resolve - Proyecto: {project_name}")
            
            return True
            
        except ImportError:
            raise ResolveConnectionError(
                "No se encontró el módulo DaVinciResolveScript.\n"
                "Asegúrate de que DaVinci Resolve esté instalado correctamente."
            )
        except Exception as e:
            raise ResolveConnectionError(f"Error al conectar: {e}")
    
    def _add_resolve_paths(self) -> None:
        """Agrega los paths del módulo de Resolve al sys.path."""
        for path in self.RESOLVE_SCRIPT_PATHS:
            path_obj = Path(path)
            if path_obj.exists() and str(path_obj) not in sys.path:
                sys.path.append(str(path_obj))
    
    def disconnect(self) -> None:
        """Desconecta de DaVinci Resolve."""
        self._resolve = None
        self._project_manager = None
        self._current_project = None
        self._media_pool = None
        self._connected = False
        logger.info("Desconectado de DaVinci Resolve")
    
    @property
    def is_connected(self) -> bool:
        """Indica si está conectado a Resolve."""
        return self._connected
    
    @property
    def resolve(self) -> Optional[Any]:
        """Retorna la instancia de Resolve."""
        return self._resolve
    
    @property
    def project(self) -> Optional[Any]:
        """Retorna el proyecto actual."""
        return self._current_project
    
    @property
    def media_pool(self) -> Optional[Any]:
        """Retorna el Media Pool."""
        return self._media_pool
    
    # =========================================================================
    # Información del Proyecto
    # =========================================================================
    
    def get_project_name(self) -> str:
        """Obtiene el nombre del proyecto actual."""
        if not self._connected:
            return ""
        return self._current_project.GetName()
    
    def get_project_settings(self) -> dict:
        """Obtiene la configuración del proyecto."""
        if not self._connected:
            return {}
        
        settings_keys = [
            "timelineFrameRate",
            "timelineResolutionWidth", 
            "timelineResolutionHeight",
            "videoMonitorFormat",
            "audioCaptureNumChannels",
        ]
        
        settings = {}
        for key in settings_keys:
            value = self._current_project.GetSetting(key)
            if value is not None:
                settings[key] = value
        
        return settings
    
    # =========================================================================
    # Timeline
    # =========================================================================
    
    def get_current_timeline(self) -> Optional[Any]:
        """Obtiene el timeline actual."""
        if not self._connected:
            return None
        return self._current_project.GetCurrentTimeline()
    
    def get_timeline_name(self) -> str:
        """Obtiene el nombre del timeline actual."""
        timeline = self.get_current_timeline()
        if timeline:
            return timeline.GetName()
        return ""
    
    def get_all_timelines(self) -> List[Any]:
        """Obtiene todos los timelines del proyecto."""
        if not self._connected:
            return []
        
        count = self._current_project.GetTimelineCount()
        return [
            self._current_project.GetTimelineByIndex(i + 1)
            for i in range(count)
        ]
    
    def set_current_timeline(self, timeline: Any) -> bool:
        """Establece el timeline actual."""
        if not self._connected:
            return False
        return self._current_project.SetCurrentTimeline(timeline)
    
    # =========================================================================
    # Media Pool
    # =========================================================================
    
    def get_root_folder(self) -> Optional[Any]:
        """Obtiene la carpeta raíz del Media Pool."""
        if not self._media_pool:
            return None
        return self._media_pool.GetRootFolder()
    
    def get_current_folder(self) -> Optional[Any]:
        """Obtiene la carpeta actual del Media Pool."""
        if not self._media_pool:
            return None
        return self._media_pool.GetCurrentFolder()
    
    def create_folder(self, name: str, parent: Optional[Any] = None) -> Optional[Any]:
        """
        Crea una carpeta en el Media Pool.
        
        Args:
            name: Nombre de la carpeta
            parent: Carpeta padre (None = carpeta actual)
            
        Returns:
            Carpeta creada o None
        """
        if not self._media_pool:
            return None
        
        if parent:
            self._media_pool.SetCurrentFolder(parent)
        
        return self._media_pool.AddSubFolder(self.get_current_folder(), name)
    
    def import_media(self, file_paths: List[str]) -> List[Any]:
        """
        Importa archivos al Media Pool.
        
        Args:
            file_paths: Lista de rutas de archivos
            
        Returns:
            Lista de clips importados
        """
        if not self._media_pool:
            return []
        
        clips = self._media_pool.ImportMedia(file_paths)
        return clips if clips else []
    
    # =========================================================================
    # Utilidades
    # =========================================================================
    
    def get_resolve_version(self) -> str:
        """Obtiene la versión de DaVinci Resolve."""
        if not self._resolve:
            return ""
        
        version = self._resolve.GetVersion()
        if isinstance(version, list):
            return ".".join(str(v) for v in version)
        return str(version)
    
    def refresh(self) -> bool:
        """
        Refresca la conexión con Resolve.
        
        Útil si el proyecto cambió externamente.
        
        Returns:
            True si el refresh fue exitoso
        """
        if not self._connected:
            return False
        
        try:
            self._current_project = self._project_manager.GetCurrentProject()
            self._media_pool = self._current_project.GetMediaPool()
            return True
        except Exception as e:
            logger.error(f"Error al refrescar: {e}")
            return False
