"""
Orquestador del Pipeline de Auto-B-Roll.

Este módulo coordina todo el flujo de procesamiento:
1. Extracción de audio
2. Transcripción (Whisper o script importado)
3. Análisis semántico
4. Búsqueda de assets
5. Descarga e inserción en timeline
"""

from typing import Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum, auto
import asyncio

from ..transcription.models import Transcription, Segment
from .pipeline import Pipeline, PipelineState


class ProcessingStage(Enum):
    """Etapas del procesamiento."""
    IDLE = auto()
    EXTRACTING_AUDIO = auto()
    TRANSCRIBING = auto()
    ANALYZING = auto()
    SEARCHING = auto()
    DOWNLOADING = auto()
    INSERTING = auto()
    COMPLETED = auto()
    ERROR = auto()


@dataclass
class ProcessingProgress:
    """Estado del progreso de procesamiento."""
    stage: ProcessingStage
    progress: float  # 0.0 - 1.0
    message: str
    current_item: Optional[str] = None
    total_items: Optional[int] = None
    completed_items: Optional[int] = None


class Orchestrator:
    """
    Orquestador principal del pipeline de Auto-B-Roll.
    
    Coordina todos los módulos del sistema para procesar un video
    desde la extracción de audio hasta la inserción en timeline.
    """
    
    def __init__(self):
        self._pipeline: Optional[Pipeline] = None
        self._current_stage = ProcessingStage.IDLE
        self._progress_callback: Optional[Callable[[ProcessingProgress], None]] = None
        self._transcription: Optional[Transcription] = None
        self._keywords: List[str] = []
        self._cancel_requested = False
    
    def set_progress_callback(self, callback: Callable[[ProcessingProgress], None]) -> None:
        """Establece el callback para reportar progreso."""
        self._progress_callback = callback
    
    def _report_progress(
        self,
        stage: ProcessingStage,
        progress: float,
        message: str,
        **kwargs
    ) -> None:
        """Reporta progreso al callback si está configurado."""
        self._current_stage = stage
        
        if self._progress_callback:
            self._progress_callback(ProcessingProgress(
                stage=stage,
                progress=progress,
                message=message,
                **kwargs
            ))
    
    async def process_video(
        self,
        video_path: Path,
        script_path: Optional[Path] = None,
        use_script_priority: bool = True
    ) -> bool:
        """
        Procesa un video completo.
        
        Args:
            video_path: Ruta al archivo de video
            script_path: Ruta opcional al archivo de guion
            use_script_priority: Si True, prioriza el texto del guion
            
        Returns:
            True si el procesamiento fue exitoso
        """
        self._cancel_requested = False
        
        try:
            # Paso 1: Extraer audio
            self._report_progress(
                ProcessingStage.EXTRACTING_AUDIO,
                0.0,
                "Extrayendo audio del video..."
            )
            
            audio_path = await self._extract_audio(video_path)
            if self._cancel_requested:
                return False
            
            # Paso 2: Transcribir
            self._report_progress(
                ProcessingStage.TRANSCRIBING,
                0.2,
                "Transcribiendo audio..."
            )
            
            if script_path and script_path.exists():
                self._transcription = await self._transcribe_with_script(
                    audio_path, 
                    script_path,
                    use_script_priority
                )
            else:
                self._transcription = await self._transcribe_audio(audio_path)
            
            if self._cancel_requested:
                return False
            
            # Paso 3: Analizar conceptos
            self._report_progress(
                ProcessingStage.ANALYZING,
                0.4,
                "Analizando conceptos visualizables..."
            )
            
            self._keywords = await self._analyze_concepts(self._transcription)
            if self._cancel_requested:
                return False
            
            # Paso 4: Buscar assets
            self._report_progress(
                ProcessingStage.SEARCHING,
                0.5,
                f"Buscando assets para {len(self._keywords)} conceptos..."
            )
            
            assets = await self._search_assets(self._keywords)
            if self._cancel_requested:
                return False
            
            # Paso 5: Descargar assets
            self._report_progress(
                ProcessingStage.DOWNLOADING,
                0.7,
                "Descargando assets seleccionados..."
            )
            
            downloaded = await self._download_assets(assets)
            if self._cancel_requested:
                return False
            
            # Paso 6: Insertar en timeline
            self._report_progress(
                ProcessingStage.INSERTING,
                0.9,
                "Insertando en timeline de DaVinci Resolve..."
            )
            
            await self._insert_in_timeline(downloaded)
            
            # Completado
            self._report_progress(
                ProcessingStage.COMPLETED,
                1.0,
                "Procesamiento completado exitosamente"
            )
            
            return True
            
        except Exception as e:
            self._report_progress(
                ProcessingStage.ERROR,
                0.0,
                f"Error: {str(e)}"
            )
            return False
    
    def cancel(self) -> None:
        """Cancela el procesamiento actual."""
        self._cancel_requested = True
    
    @property
    def current_stage(self) -> ProcessingStage:
        """Retorna la etapa actual del procesamiento."""
        return self._current_stage
    
    @property
    def transcription(self) -> Optional[Transcription]:
        """Retorna la transcripción actual."""
        return self._transcription
    
    @property
    def keywords(self) -> List[str]:
        """Retorna las palabras clave extraídas."""
        return self._keywords
    
    # =========================================================================
    # Métodos internos (a implementar con los módulos reales)
    # =========================================================================
    
    async def _extract_audio(self, video_path: Path) -> Path:
        """Extrae el audio del video."""
        # TODO: Implementar con AudioExtractor
        # Por ahora, simular
        await asyncio.sleep(0.5)
        return video_path.with_suffix(".wav")
    
    async def _transcribe_audio(self, audio_path: Path) -> Transcription:
        """Transcribe el audio usando Whisper."""
        # TODO: Implementar con WhisperService
        await asyncio.sleep(1.0)
        
        return Transcription(
            source_file=str(audio_path),
            language="es",
            segments=[
                Segment(
                    start=0.0,
                    end=5.0,
                    text="Ejemplo de transcripción automática.",
                    keywords=["ejemplo", "transcripción"]
                )
            ]
        )
    
    async def _transcribe_with_script(
        self,
        audio_path: Path,
        script_path: Path,
        use_priority: bool
    ) -> Transcription:
        """Transcribe usando el guion como referencia."""
        # TODO: Implementar con ScriptImporter + Aligner
        await asyncio.sleep(1.0)
        
        script_text = script_path.read_text(encoding="utf-8")
        
        return Transcription(
            source_file=str(audio_path),
            language="es",
            segments=[
                Segment(
                    start=0.0,
                    end=10.0,
                    text=script_text[:200],
                    keywords=[]
                )
            ]
        )
    
    async def _analyze_concepts(self, transcription: Transcription) -> List[str]:
        """Analiza la transcripción para extraer conceptos."""
        # TODO: Implementar con SemanticAnalyzer
        await asyncio.sleep(0.5)
        
        # Simular extracción de keywords
        all_keywords = []
        for segment in transcription.segments:
            all_keywords.extend(segment.keywords)
        
        return list(set(all_keywords)) or ["ejemplo", "video", "automatización"]
    
    async def _search_assets(self, keywords: List[str]) -> List[dict]:
        """Busca assets para las palabras clave."""
        # TODO: Implementar con StockAggregator
        await asyncio.sleep(1.0)
        
        return [
            {"id": f"asset_{i}", "keyword": kw, "source": "pexels"}
            for i, kw in enumerate(keywords)
        ]
    
    async def _download_assets(self, assets: List[dict]) -> List[Path]:
        """Descarga los assets seleccionados."""
        # TODO: Implementar con AssetDownloader
        await asyncio.sleep(1.0)
        
        return []
    
    async def _insert_in_timeline(self, asset_paths: List[Path]) -> None:
        """Inserta los assets en el timeline de DaVinci."""
        # TODO: Implementar con ResolveAPI + TimelineManager
        await asyncio.sleep(0.5)
