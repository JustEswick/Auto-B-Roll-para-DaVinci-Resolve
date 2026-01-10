"""
Servicio de Transcripción con Whisper.

Este módulo proporciona una interfaz para transcribir audio
utilizando OpenAI Whisper.
"""

from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
import logging

from .models import Transcription, Segment, Word

logger = logging.getLogger(__name__)


class WhisperError(Exception):
    """Error durante la transcripción con Whisper."""
    pass


class WhisperService:
    """
    Servicio de transcripción con OpenAI Whisper.
    
    Proporciona métodos para transcribir audio con diferentes
    modelos y configuraciones.
    """
    
    AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large"]
    
    LANGUAGE_CODES = {
        "Español": "es",
        "English": "en",
        "Auto-detectar": None,
    }
    
    def __init__(
        self,
        model_name: str = "base",
        device: Optional[str] = None
    ):
        """
        Inicializa el servicio de Whisper.
        
        Args:
            model_name: Nombre del modelo a usar
            device: Dispositivo para inferencia ('cuda', 'cpu', None para auto)
        """
        self._model_name = model_name
        self._device = device
        self._model = None
        self._loaded = False
    
    def _ensure_model_loaded(self) -> None:
        """Carga el modelo si no está cargado."""
        if self._loaded:
            return
        
        try:
            import whisper
            
            logger.info(f"Cargando modelo Whisper '{self._model_name}'...")
            self._model = whisper.load_model(
                self._model_name,
                device=self._device
            )
            self._loaded = True
            logger.info(f"Modelo Whisper '{self._model_name}' cargado exitosamente")
            
        except ImportError:
            raise WhisperError(
                "OpenAI Whisper no está instalado.\n"
                "Instálalo con: pip install openai-whisper"
            )
        except Exception as e:
            raise WhisperError(f"Error al cargar el modelo: {e}")
    
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        word_timestamps: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Transcription:
        """
        Transcribe un archivo de audio.
        
        Args:
            audio_path: Ruta al archivo de audio
            language: Código de idioma (ej: 'es', 'en') o None para auto-detectar
            word_timestamps: Si True, incluye timestamps por palabra
            progress_callback: Callback para reportar progreso (0.0 - 1.0)
            
        Returns:
            Objeto Transcription con los resultados
            
        Raises:
            WhisperError: Si la transcripción falla
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise WhisperError(f"El archivo de audio no existe: {audio_path}")
        
        self._ensure_model_loaded()
        
        logger.info(f"Transcribiendo: {audio_path.name}")
        
        try:
            # Configuración de transcripción
            options: Dict[str, Any] = {
                "task": "transcribe",
                "word_timestamps": word_timestamps,
                "verbose": False,
            }
            
            if language:
                options["language"] = language
            
            # Ejecutar transcripción
            result = self._model.transcribe(str(audio_path), **options)
            
            # Procesar resultados
            segments = self._process_segments(result)
            
            transcription = Transcription(
                source_file=str(audio_path),
                language=result.get("language", language or "unknown"),
                model=f"whisper-{self._model_name}",
                segments=segments,
            )
            
            logger.info(
                f"Transcripción completada: {len(segments)} segmentos, "
                f"{transcription.word_count} palabras"
            )
            
            return transcription
            
        except Exception as e:
            raise WhisperError(f"Error durante la transcripción: {e}")
    
    def _process_segments(self, result: Dict[str, Any]) -> List[Segment]:
        """
        Procesa los segmentos del resultado de Whisper.
        
        Args:
            result: Resultado de whisper.transcribe()
            
        Returns:
            Lista de objetos Segment
        """
        segments = []
        
        for seg_data in result.get("segments", []):
            # Procesar palabras si están disponibles
            words = []
            if "words" in seg_data:
                for word_data in seg_data["words"]:
                    words.append(Word(
                        text=word_data.get("word", "").strip(),
                        start=word_data.get("start", 0.0),
                        end=word_data.get("end", 0.0),
                        confidence=word_data.get("probability", 1.0),
                    ))
            
            segment = Segment(
                start=seg_data.get("start", 0.0),
                end=seg_data.get("end", 0.0),
                text=seg_data.get("text", "").strip(),
                words=words,
                confidence=seg_data.get("avg_logprob", 0.0),
            )
            
            segments.append(segment)
        
        return segments
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Obtiene información sobre el modelo cargado.
        
        Returns:
            Diccionario con información del modelo
        """
        return {
            "model": self._model_name,
            "loaded": self._loaded,
            "device": self._device,
            "available_models": self.AVAILABLE_MODELS,
        }
    
    def unload_model(self) -> None:
        """Descarga el modelo de la memoria."""
        if self._model is not None:
            del self._model
            self._model = None
            self._loaded = False
            logger.info("Modelo Whisper descargado de memoria")
    
    @staticmethod
    def estimate_processing_time(audio_duration: float, model: str = "base") -> float:
        """
        Estima el tiempo de procesamiento.
        
        Args:
            audio_duration: Duración del audio en segundos
            model: Nombre del modelo
            
        Returns:
            Tiempo estimado en segundos
        """
        # Factores aproximados basados en benchmarks
        # (tiempo de procesamiento / tiempo de audio)
        model_factors = {
            "tiny": 0.1,
            "base": 0.2,
            "small": 0.5,
            "medium": 1.0,
            "large": 2.0,
        }
        
        factor = model_factors.get(model, 0.5)
        return audio_duration * factor
