"""
Extractor de Audio.

Este módulo extrae la pista de audio de archivos de video
para su posterior procesamiento con Whisper.
"""

from typing import Optional
from pathlib import Path
import subprocess
import tempfile
import logging

logger = logging.getLogger(__name__)


class AudioExtractionError(Exception):
    """Error durante la extracción de audio."""
    pass


class AudioExtractor:
    """
    Extractor de audio de archivos de video.
    
    Utiliza FFmpeg para extraer la pista de audio y convertirla
    al formato requerido por Whisper (WAV, 16kHz, mono).
    """
    
    # Formatos de video soportados
    SUPPORTED_VIDEO_FORMATS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}
    
    # Formatos de audio soportados (para procesamiento directo)
    SUPPORTED_AUDIO_FORMATS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inicializa el extractor.
        
        Args:
            output_dir: Directorio para archivos extraídos.
                       Si es None, usa un directorio temporal.
        """
        self._output_dir = output_dir
        self._ffmpeg_path = self._find_ffmpeg()
    
    def _find_ffmpeg(self) -> str:
        """Busca el ejecutable de FFmpeg."""
        # Intentar encontrar ffmpeg en el PATH
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return "ffmpeg"
        except FileNotFoundError:
            pass
        
        # Rutas comunes en Windows
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        logger.warning("FFmpeg no encontrado. La extracción de audio puede fallar.")
        return "ffmpeg"  # Intentar de todos modos
    
    def is_supported(self, file_path: Path) -> bool:
        """
        Verifica si el archivo es soportado.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            True si el formato es soportado
        """
        suffix = file_path.suffix.lower()
        return suffix in self.SUPPORTED_VIDEO_FORMATS | self.SUPPORTED_AUDIO_FORMATS
    
    def extract(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        sample_rate: int = 16000,
        channels: int = 1
    ) -> Path:
        """
        Extrae el audio de un archivo de video.
        
        Args:
            input_path: Ruta al archivo de video
            output_path: Ruta de salida (opcional)
            sample_rate: Frecuencia de muestreo (default: 16kHz para Whisper)
            channels: Número de canales (default: 1 para mono)
            
        Returns:
            Ruta al archivo de audio extraído
            
        Raises:
            AudioExtractionError: Si la extracción falla
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise AudioExtractionError(f"El archivo no existe: {input_path}")
        
        if not self.is_supported(input_path):
            raise AudioExtractionError(
                f"Formato no soportado: {input_path.suffix}\n"
                f"Formatos válidos: {self.SUPPORTED_VIDEO_FORMATS | self.SUPPORTED_AUDIO_FORMATS}"
            )
        
        # Determinar ruta de salida
        if output_path is None:
            if self._output_dir:
                self._output_dir.mkdir(parents=True, exist_ok=True)
                output_path = self._output_dir / f"{input_path.stem}_audio.wav"
            else:
                # Usar directorio temporal
                temp_dir = Path(tempfile.gettempdir()) / "auto_broll"
                temp_dir.mkdir(parents=True, exist_ok=True)
                output_path = temp_dir / f"{input_path.stem}_audio.wav"
        
        output_path = Path(output_path)
        
        # Si el archivo de entrada ya es audio WAV con las especificaciones correctas,
        # podríamos copiarlo directamente, pero por seguridad lo procesamos
        
        # Construir comando FFmpeg
        cmd = [
            self._ffmpeg_path,
            "-y",  # Sobrescribir sin preguntar
            "-i", str(input_path),
            "-vn",  # Sin video
            "-acodec", "pcm_s16le",  # Codec PCM 16-bit
            "-ar", str(sample_rate),  # Sample rate
            "-ac", str(channels),  # Canales
            str(output_path)
        ]
        
        logger.info(f"Extrayendo audio: {input_path.name} -> {output_path.name}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos máximo
            )
            
            if result.returncode != 0:
                error_msg = result.stderr[:500] if result.stderr else "Error desconocido"
                raise AudioExtractionError(f"FFmpeg falló: {error_msg}")
            
            if not output_path.exists():
                raise AudioExtractionError("El archivo de salida no fue creado")
            
            logger.info(f"Audio extraído: {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
            return output_path
            
        except subprocess.TimeoutExpired:
            raise AudioExtractionError("Timeout: La extracción tomó demasiado tiempo")
        except FileNotFoundError:
            raise AudioExtractionError(
                "FFmpeg no está instalado o no se encuentra en el PATH.\n"
                "Por favor, instala FFmpeg: https://ffmpeg.org/download.html"
            )
    
    def get_duration(self, file_path: Path) -> float:
        """
        Obtiene la duración de un archivo de audio/video.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            Duración en segundos
        """
        cmd = [
            self._ffmpeg_path.replace("ffmpeg", "ffprobe"),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            pass
        
        return 0.0
    
    def cleanup_temp_files(self) -> None:
        """Limpia archivos temporales creados."""
        temp_dir = Path(tempfile.gettempdir()) / "auto_broll"
        if temp_dir.exists():
            for file in temp_dir.glob("*_audio.wav"):
                try:
                    file.unlink()
                    logger.debug(f"Eliminado: {file}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar {file}: {e}")
