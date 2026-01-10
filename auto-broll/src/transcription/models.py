"""
Modelos de datos para transcripción.

Define las estructuras de datos utilizadas para representar
transcripciones y segmentos de audio.
"""

from typing import Optional, List
from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class Word:
    """Representa una palabra con su timestamp."""
    text: str
    start: float  # Segundos
    end: float
    confidence: float = 1.0
    
    @property
    def duration(self) -> float:
        """Duración de la palabra en segundos."""
        return self.end - self.start
    
    def format_timestamp(self) -> str:
        """Formatea el timestamp como HH:MM:SS.mmm"""
        td = timedelta(seconds=self.start)
        return str(td)[:-3] if '.' in str(td) else f"{td}.000"


@dataclass
class Segment:
    """
    Representa un segmento de transcripción.
    
    Un segmento es una frase o grupo de palabras con un rango
    de tiempo definido.
    """
    start: float  # Segundos
    end: float
    text: str
    keywords: List[str] = field(default_factory=list)
    words: List[Word] = field(default_factory=list)
    speaker: Optional[str] = None
    confidence: float = 1.0
    visualizable: bool = True
    
    @property
    def duration(self) -> float:
        """Duración del segmento en segundos."""
        return self.end - self.start
    
    def format_time_range(self) -> str:
        """Formatea el rango de tiempo como MM:SS - MM:SS"""
        start_str = f"{int(self.start // 60):02d}:{int(self.start % 60):02d}"
        end_str = f"{int(self.end // 60):02d}:{int(self.end % 60):02d}"
        return f"{start_str} - {end_str}"
    
    def to_srt_format(self, index: int) -> str:
        """Convierte el segmento a formato SRT."""
        start_td = timedelta(seconds=self.start)
        end_td = timedelta(seconds=self.end)
        
        def format_srt_time(td: timedelta) -> str:
            total_seconds = td.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            milliseconds = int((total_seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        
        return (
            f"{index}\n"
            f"{format_srt_time(start_td)} --> {format_srt_time(end_td)}\n"
            f"{self.text}\n"
        )


@dataclass
class Transcription:
    """
    Representa una transcripción completa.
    
    Contiene todos los segmentos de la transcripción junto con
    metadatos del archivo fuente y configuración utilizada.
    """
    source_file: str
    language: str = "es"
    model: str = "whisper-base"
    segments: List[Segment] = field(default_factory=list)
    full_text: str = ""
    duration: float = 0.0
    word_count: int = 0
    
    def __post_init__(self):
        """Calcula campos derivados después de la inicialización."""
        if not self.full_text and self.segments:
            self.full_text = " ".join(seg.text for seg in self.segments)
        
        if not self.word_count and self.full_text:
            self.word_count = len(self.full_text.split())
        
        if not self.duration and self.segments:
            self.duration = max(seg.end for seg in self.segments)
    
    def get_segment_at_time(self, time_seconds: float) -> Optional[Segment]:
        """
        Obtiene el segmento que contiene el tiempo especificado.
        
        Args:
            time_seconds: Tiempo en segundos
            
        Returns:
            Segmento que contiene el tiempo, o None
        """
        for segment in self.segments:
            if segment.start <= time_seconds <= segment.end:
                return segment
        return None
    
    def get_segments_in_range(
        self,
        start: float,
        end: float
    ) -> List[Segment]:
        """
        Obtiene los segmentos dentro de un rango de tiempo.
        
        Args:
            start: Tiempo de inicio en segundos
            end: Tiempo de fin en segundos
            
        Returns:
            Lista de segmentos en el rango
        """
        return [
            seg for seg in self.segments
            if seg.start < end and seg.end > start
        ]
    
    def get_all_keywords(self) -> List[str]:
        """Obtiene todas las palabras clave únicas."""
        keywords = set()
        for segment in self.segments:
            keywords.update(segment.keywords)
        return sorted(keywords)
    
    def to_srt(self) -> str:
        """Convierte la transcripción a formato SRT."""
        lines = []
        for i, segment in enumerate(self.segments, 1):
            lines.append(segment.to_srt_format(i))
        return "\n".join(lines)
    
    def to_vtt(self) -> str:
        """Convierte la transcripción a formato WebVTT."""
        lines = ["WEBVTT", ""]
        
        for segment in self.segments:
            start_td = timedelta(seconds=segment.start)
            end_td = timedelta(seconds=segment.end)
            
            def format_vtt_time(td: timedelta) -> str:
                total_seconds = td.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                seconds = int(total_seconds % 60)
                milliseconds = int((total_seconds % 1) * 1000)
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            
            lines.append(
                f"{format_vtt_time(start_td)} --> {format_vtt_time(end_td)}"
            )
            lines.append(segment.text)
            lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convierte la transcripción a diccionario."""
        return {
            "source_file": self.source_file,
            "language": self.language,
            "model": self.model,
            "duration": self.duration,
            "word_count": self.word_count,
            "full_text": self.full_text,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "keywords": seg.keywords,
                    "confidence": seg.confidence,
                }
                for seg in self.segments
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Transcription":
        """Crea una transcripción desde un diccionario."""
        segments = [
            Segment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"],
                keywords=seg.get("keywords", []),
                confidence=seg.get("confidence", 1.0),
            )
            for seg in data.get("segments", [])
        ]
        
        return cls(
            source_file=data.get("source_file", ""),
            language=data.get("language", "es"),
            model=data.get("model", "whisper-base"),
            segments=segments,
            full_text=data.get("full_text", ""),
            duration=data.get("duration", 0.0),
            word_count=data.get("word_count", 0),
        )
