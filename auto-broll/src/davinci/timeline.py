"""
Gestor de Timeline de DaVinci Resolve.

Este módulo proporciona funciones de alto nivel para
manipular el timeline de DaVinci Resolve.
"""

from typing import Optional, List, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

from .resolve_api import ResolveAPI

logger = logging.getLogger(__name__)


@dataclass
class ClipInfo:
    """Información de un clip en el timeline."""
    name: str
    start_frame: int
    end_frame: int
    duration: int
    track_index: int
    clip_type: str  # video, audio
    media_pool_item: Optional[Any] = None
    
    @property
    def start_seconds(self) -> float:
        """Tiempo de inicio en segundos (asumiendo 24fps)."""
        return self.start_frame / 24.0
    
    @property
    def end_seconds(self) -> float:
        """Tiempo de fin en segundos."""
        return self.end_frame / 24.0


class TimelineManager:
    """
    Gestor de timeline para DaVinci Resolve.
    
    Proporciona métodos para insertar clips, gestionar tracks
    y manipular el timeline.
    """
    
    def __init__(self, resolve_api: ResolveAPI):
        """
        Inicializa el gestor.
        
        Args:
            resolve_api: Instancia de ResolveAPI conectada
        """
        self._api = resolve_api
        self._timeline = None
    
    def _ensure_timeline(self) -> bool:
        """Asegura que hay un timeline válido."""
        if not self._api.is_connected:
            logger.error("No hay conexión con DaVinci Resolve")
            return False
        
        self._timeline = self._api.get_current_timeline()
        if not self._timeline:
            logger.error("No hay timeline activo")
            return False
        
        return True
    
    @property
    def timeline(self) -> Optional[Any]:
        """Retorna el timeline actual."""
        self._ensure_timeline()
        return self._timeline
    
    # =========================================================================
    # Información del Timeline
    # =========================================================================
    
    def get_name(self) -> str:
        """Obtiene el nombre del timeline."""
        if not self._ensure_timeline():
            return ""
        return self._timeline.GetName()
    
    def get_frame_rate(self) -> float:
        """Obtiene el frame rate del timeline."""
        if not self._ensure_timeline():
            return 24.0
        
        settings = self._timeline.GetSetting("timelineFrameRate")
        return float(settings) if settings else 24.0
    
    def get_duration_frames(self) -> int:
        """Obtiene la duración en frames."""
        if not self._ensure_timeline():
            return 0
        
        end_frame = self._timeline.GetEndFrame()
        start_frame = self._timeline.GetStartFrame()
        return end_frame - start_frame
    
    def get_duration_seconds(self) -> float:
        """Obtiene la duración en segundos."""
        fps = self.get_frame_rate()
        frames = self.get_duration_frames()
        return frames / fps if fps > 0 else 0.0
    
    def get_track_count(self, track_type: str = "video") -> int:
        """
        Obtiene el número de tracks.
        
        Args:
            track_type: 'video' o 'audio'
            
        Returns:
            Número de tracks
        """
        if not self._ensure_timeline():
            return 0
        
        return self._timeline.GetTrackCount(track_type)
    
    # =========================================================================
    # Inserción de Clips
    # =========================================================================
    
    def insert_clip(
        self,
        media_pool_item: Any,
        start_seconds: float,
        duration_seconds: float,
        track_index: int = 2,
        with_fade: bool = True,
        fade_duration: float = 0.5
    ) -> bool:
        """
        Inserta un clip en el timeline.
        
        Args:
            media_pool_item: Item del Media Pool a insertar
            start_seconds: Tiempo de inicio en segundos
            duration_seconds: Duración en segundos
            track_index: Índice del track (1-based)
            with_fade: Si aplica fade in/out
            fade_duration: Duración del fade en segundos
            
        Returns:
            True si la inserción fue exitosa
        """
        if not self._ensure_timeline():
            return False
        
        media_pool = self._api.media_pool
        if not media_pool:
            return False
        
        fps = self.get_frame_rate()
        
        # Convertir a frames
        start_frame = int(start_seconds * fps)
        duration_frames = int(duration_seconds * fps)
        end_frame = start_frame + duration_frames
        
        # Asegurar que hay suficientes tracks
        current_tracks = self.get_track_count("video")
        while current_tracks < track_index:
            self._timeline.AddTrack("video")
            current_tracks += 1
        
        try:
            # Crear clip info para inserción
            clip_info = {
                "mediaPoolItem": media_pool_item,
                "startFrame": start_frame,
                "endFrame": end_frame,
                "trackIndex": track_index,
                "recordFrame": start_frame,  # Posición en el timeline
            }
            
            # Insertar clip
            result = media_pool.AppendToTimeline([clip_info])
            
            if result:
                logger.info(
                    f"Clip insertado en track {track_index} "
                    f"({start_seconds:.2f}s - {start_seconds + duration_seconds:.2f}s)"
                )
                
                # TODO: Aplicar fades si with_fade es True
                
                return True
            else:
                logger.error("Error al insertar clip en timeline")
                return False
                
        except Exception as e:
            logger.error(f"Error al insertar clip: {e}")
            return False
    
    def insert_clip_at_playhead(
        self,
        media_pool_item: Any,
        track_index: int = 2,
        duration_seconds: Optional[float] = None
    ) -> bool:
        """
        Inserta un clip en la posición del playhead.
        
        Args:
            media_pool_item: Item del Media Pool
            track_index: Índice del track
            duration_seconds: Duración opcional (None = duración original)
            
        Returns:
            True si fue exitoso
        """
        if not self._ensure_timeline():
            return False
        
        playhead_frame = self._timeline.GetCurrentVideoItem()
        fps = self.get_frame_rate()
        
        # Obtener posición del playhead
        # Note: La API de Resolve puede variar, esto es aproximado
        start_seconds = 0  # TODO: Obtener posición real del playhead
        
        if duration_seconds is None:
            duration_seconds = 3.0  # Duración por defecto
        
        return self.insert_clip(
            media_pool_item,
            start_seconds,
            duration_seconds,
            track_index
        )
    
    # =========================================================================
    # Gestión de Clips
    # =========================================================================
    
    def get_clips_in_track(self, track_index: int = 1) -> List[ClipInfo]:
        """
        Obtiene todos los clips de un track.
        
        Args:
            track_index: Índice del track (1-based)
            
        Returns:
            Lista de información de clips
        """
        if not self._ensure_timeline():
            return []
        
        clips_info = []
        
        try:
            items = self._timeline.GetItemListInTrack("video", track_index)
            
            if items:
                for item in items:
                    info = ClipInfo(
                        name=item.GetName(),
                        start_frame=item.GetStart(),
                        end_frame=item.GetEnd(),
                        duration=item.GetDuration(),
                        track_index=track_index,
                        clip_type="video",
                        media_pool_item=item.GetMediaPoolItem(),
                    )
                    clips_info.append(info)
                    
        except Exception as e:
            logger.error(f"Error obteniendo clips: {e}")
        
        return clips_info
    
    def find_gaps(
        self,
        track_index: int = 1,
        min_gap_seconds: float = 2.0
    ) -> List[Tuple[float, float]]:
        """
        Encuentra huecos en un track donde se puede insertar B-Roll.
        
        Args:
            track_index: Índice del track a analizar
            min_gap_seconds: Duración mínima del hueco en segundos
            
        Returns:
            Lista de tuplas (start_seconds, end_seconds) de huecos
        """
        clips = self.get_clips_in_track(track_index)
        
        if not clips:
            return []
        
        fps = self.get_frame_rate()
        min_gap_frames = int(min_gap_seconds * fps)
        
        # Ordenar clips por tiempo de inicio
        clips.sort(key=lambda c: c.start_frame)
        
        gaps = []
        
        # Buscar huecos entre clips
        for i in range(len(clips) - 1):
            current_end = clips[i].end_frame
            next_start = clips[i + 1].start_frame
            
            gap_frames = next_start - current_end
            
            if gap_frames >= min_gap_frames:
                gap_start = current_end / fps
                gap_end = next_start / fps
                gaps.append((gap_start, gap_end))
        
        return gaps
    
    # =========================================================================
    # Markers
    # =========================================================================
    
    def add_marker(
        self,
        frame: int,
        color: str = "Blue",
        name: str = "",
        note: str = ""
    ) -> bool:
        """
        Agrega un marcador al timeline.
        
        Args:
            frame: Frame donde agregar el marcador
            color: Color del marcador (Blue, Cyan, Green, Yellow, Red, Pink, Purple, Fuchsia, Rose, Lavender, Sky, Mint, Lemon, Sand, Cocoa, Cream)
            name: Nombre del marcador
            note: Nota del marcador
            
        Returns:
            True si fue exitoso
        """
        if not self._ensure_timeline():
            return False
        
        try:
            return self._timeline.AddMarker(
                frame,
                color,
                name,
                note,
                1  # Duración en frames
            )
        except Exception as e:
            logger.error(f"Error agregando marcador: {e}")
            return False
    
    def get_markers(self) -> dict:
        """Obtiene todos los marcadores del timeline."""
        if not self._ensure_timeline():
            return {}
        
        return self._timeline.GetMarkers() or {}
