"""
Pipeline de Procesamiento.

Define el flujo de datos y estados del pipeline de Auto-B-Roll.
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import time


class PipelineState(Enum):
    """Estados posibles del pipeline."""
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class PipelineStep:
    """Representa un paso del pipeline."""
    name: str
    description: str
    weight: float = 1.0  # Peso relativo para cálculo de progreso
    completed: bool = False
    duration: float = 0.0  # Tiempo de ejecución en segundos
    result: Any = None
    error: Optional[str] = None


@dataclass
class PipelineContext:
    """Contexto compartido entre pasos del pipeline."""
    
    # Archivos de entrada
    video_path: Optional[Path] = None
    script_path: Optional[Path] = None
    
    # Archivos intermedios
    audio_path: Optional[Path] = None
    
    # Datos procesados
    transcription_text: str = ""
    transcription_segments: List[Dict] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # Assets
    found_assets: List[Dict] = field(default_factory=list)
    selected_assets: List[str] = field(default_factory=list)
    downloaded_assets: List[Path] = field(default_factory=list)
    
    # Configuración
    language: str = "es"
    whisper_model: str = "base"
    use_script_priority: bool = True
    
    # Metadatos
    start_time: float = 0.0
    end_time: float = 0.0


class Pipeline:
    """
    Pipeline de procesamiento de Auto-B-Roll.
    
    Maneja el flujo de ejecución de los pasos de procesamiento,
    permite pausar, reanudar y cancelar la ejecución.
    """
    
    def __init__(self):
        self._state = PipelineState.IDLE
        self._steps: List[PipelineStep] = []
        self._current_step_index = 0
        self._context = PipelineContext()
        self._progress_callback: Optional[Callable[[float, str], None]] = None
    
    @property
    def state(self) -> PipelineState:
        """Retorna el estado actual del pipeline."""
        return self._state
    
    @property
    def context(self) -> PipelineContext:
        """Retorna el contexto del pipeline."""
        return self._context
    
    @property
    def progress(self) -> float:
        """Calcula el progreso total del pipeline (0.0 - 1.0)."""
        if not self._steps:
            return 0.0
        
        total_weight = sum(step.weight for step in self._steps)
        completed_weight = sum(
            step.weight for step in self._steps if step.completed
        )
        
        return completed_weight / total_weight if total_weight > 0 else 0.0
    
    @property
    def current_step(self) -> Optional[PipelineStep]:
        """Retorna el paso actual."""
        if 0 <= self._current_step_index < len(self._steps):
            return self._steps[self._current_step_index]
        return None
    
    def set_progress_callback(
        self, 
        callback: Callable[[float, str], None]
    ) -> None:
        """Establece el callback para reportar progreso."""
        self._progress_callback = callback
    
    def _report_progress(self, message: str) -> None:
        """Reporta el progreso actual."""
        if self._progress_callback:
            self._progress_callback(self.progress, message)
    
    def add_step(
        self,
        name: str,
        description: str,
        weight: float = 1.0
    ) -> None:
        """Añade un paso al pipeline."""
        self._steps.append(PipelineStep(
            name=name,
            description=description,
            weight=weight
        ))
    
    def setup_default_steps(self) -> None:
        """Configura los pasos por defecto del pipeline."""
        self._steps.clear()
        
        self.add_step(
            "extract_audio",
            "Extrayendo audio del video",
            weight=1.0
        )
        self.add_step(
            "transcribe",
            "Transcribiendo audio",
            weight=3.0  # Paso más pesado
        )
        self.add_step(
            "analyze",
            "Analizando conceptos",
            weight=1.0
        )
        self.add_step(
            "search",
            "Buscando assets",
            weight=2.0
        )
        self.add_step(
            "download",
            "Descargando assets",
            weight=2.0
        )
        self.add_step(
            "insert",
            "Insertando en timeline",
            weight=1.0
        )
    
    def start(self, video_path: Path, script_path: Optional[Path] = None) -> None:
        """Inicia el pipeline."""
        if self._state == PipelineState.RUNNING:
            raise RuntimeError("El pipeline ya está en ejecución")
        
        self._context = PipelineContext(
            video_path=video_path,
            script_path=script_path,
            start_time=time.time()
        )
        
        self._state = PipelineState.RUNNING
        self._current_step_index = 0
        
        # Resetear pasos
        for step in self._steps:
            step.completed = False
            step.duration = 0.0
            step.result = None
            step.error = None
    
    def complete_current_step(self, result: Any = None) -> None:
        """Marca el paso actual como completado."""
        if self.current_step:
            self.current_step.completed = True
            self.current_step.result = result
            self._current_step_index += 1
            
            self._report_progress(
                f"Completado: {self.current_step.description}" 
                if self.current_step else "Pipeline completado"
            )
            
            if self._current_step_index >= len(self._steps):
                self._state = PipelineState.COMPLETED
                self._context.end_time = time.time()
    
    def fail_current_step(self, error: str) -> None:
        """Marca el paso actual como fallido."""
        if self.current_step:
            self.current_step.error = error
        
        self._state = PipelineState.FAILED
        self._context.end_time = time.time()
    
    def pause(self) -> None:
        """Pausa el pipeline."""
        if self._state == PipelineState.RUNNING:
            self._state = PipelineState.PAUSED
    
    def resume(self) -> None:
        """Reanuda el pipeline."""
        if self._state == PipelineState.PAUSED:
            self._state = PipelineState.RUNNING
    
    def cancel(self) -> None:
        """Cancela el pipeline."""
        self._state = PipelineState.CANCELLED
        self._context.end_time = time.time()
    
    def reset(self) -> None:
        """Resetea el pipeline a su estado inicial."""
        self._state = PipelineState.IDLE
        self._current_step_index = 0
        self._context = PipelineContext()
        
        for step in self._steps:
            step.completed = False
            step.duration = 0.0
            step.result = None
            step.error = None
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna un resumen del estado del pipeline."""
        return {
            "state": self._state.name,
            "progress": self.progress,
            "current_step": self.current_step.name if self.current_step else None,
            "steps": [
                {
                    "name": step.name,
                    "completed": step.completed,
                    "error": step.error
                }
                for step in self._steps
            ],
            "duration": (
                self._context.end_time - self._context.start_time
                if self._context.end_time > 0
                else time.time() - self._context.start_time
                if self._context.start_time > 0
                else 0
            )
        }
