"""
Alineador de Guion con Audio.

Este módulo alinea el texto de un guion importado con los
timestamps del audio usando algoritmos de alineación forzada.
"""

from typing import Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass
import logging

from .models import Transcription, Segment, Word
from .script_importer import ImportedScript, ScriptLine

logger = logging.getLogger(__name__)


class AlignmentError(Exception):
    """Error durante la alineación."""
    pass


@dataclass
class AlignedSegment:
    """Segmento alineado con timestamps del audio."""
    text: str  # Texto del guion
    transcribed_text: str  # Texto transcrito (puede diferir)
    start: float
    end: float
    confidence: float  # Confianza de la alineación
    has_discrepancy: bool  # Si hay diferencia significativa


class ForcedAligner:
    """
    Alineador forzado de guion con audio.
    
    Utiliza la transcripción de Whisper para alinear el texto
    del guion con los timestamps precisos del audio.
    """
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        Inicializa el alineador.
        
        Args:
            similarity_threshold: Umbral mínimo de similitud para considerar
                                  que dos textos coinciden (0.0 - 1.0)
        """
        self._similarity_threshold = similarity_threshold
    
    def align(
        self,
        script: ImportedScript,
        transcription: Transcription,
        use_script_text: bool = True
    ) -> Transcription:
        """
        Alinea un guion con la transcripción.
        
        Args:
            script: Guion importado
            transcription: Transcripción de Whisper
            use_script_text: Si True, usa el texto del guion en el resultado
            
        Returns:
            Nueva transcripción con timestamps alineados
        """
        logger.info("Iniciando alineación de guion con transcripción...")
        
        # Si el script ya tiene timestamps (SRT), usarlos directamente
        if script.has_timestamps:
            return self._align_with_srt_timestamps(script, transcription, use_script_text)
        
        # Sino, usar alineación por similitud
        return self._align_by_similarity(script, transcription, use_script_text)
    
    def _align_with_srt_timestamps(
        self,
        script: ImportedScript,
        transcription: Transcription,
        use_script_text: bool
    ) -> Transcription:
        """
        Alinea usando timestamps del SRT.
        
        Cuando el script es un SRT, usamos sus timestamps directamente
        pero podemos mejorar la precisión con la transcripción.
        """
        segments = []
        
        for line in script.lines:
            if line.start_time is not None and line.end_time is not None:
                # Buscar el segmento de transcripción más cercano
                closest_seg = self._find_closest_segment(
                    transcription.segments,
                    line.start_time
                )
                
                # Calcular similitud
                confidence = 1.0
                if closest_seg:
                    confidence = self._calculate_similarity(
                        line.text,
                        closest_seg.text
                    )
                
                text = line.text if use_script_text else (
                    closest_seg.text if closest_seg else line.text
                )
                
                segments.append(Segment(
                    start=line.start_time,
                    end=line.end_time,
                    text=text,
                    confidence=confidence,
                ))
        
        return Transcription(
            source_file=transcription.source_file,
            language=transcription.language,
            model=f"{transcription.model}+aligned",
            segments=segments,
        )
    
    def _align_by_similarity(
        self,
        script: ImportedScript,
        transcription: Transcription,
        use_script_text: bool
    ) -> Transcription:
        """
        Alinea usando similitud de texto.
        
        Para scripts sin timestamps, buscamos coincidencias en la
        transcripción para determinar los tiempos.
        """
        aligned_segments = []
        script_words = script.full_text.lower().split()
        
        # Crear un índice de palabras de la transcripción
        trans_words: List[Tuple[Word, int]] = []  # (palabra, índice de segmento)
        for seg_idx, segment in enumerate(transcription.segments):
            if segment.words:
                for word in segment.words:
                    trans_words.append((word, seg_idx))
        
        if not trans_words:
            # Si no hay palabras individuales, alinear por segmentos
            return self._align_segments_rough(script, transcription, use_script_text)
        
        # Alineación por ventana deslizante
        current_pos = 0
        
        for line in script.lines:
            line_words = line.text.lower().split()
            
            if not line_words:
                continue
            
            # Buscar el mejor match en la transcripción
            best_start_idx, best_end_idx, confidence = self._find_best_match(
                line_words,
                trans_words,
                current_pos
            )
            
            if best_start_idx is not None and best_end_idx is not None:
                start_word, _ = trans_words[best_start_idx]
                end_word, _ = trans_words[best_end_idx]
                
                text = line.text if use_script_text else " ".join(
                    w.text for w, _ in trans_words[best_start_idx:best_end_idx+1]
                )
                
                aligned_segments.append(Segment(
                    start=start_word.start,
                    end=end_word.end,
                    text=text,
                    confidence=confidence,
                ))
                
                current_pos = best_end_idx + 1
        
        return Transcription(
            source_file=transcription.source_file,
            language=transcription.language,
            model=f"{transcription.model}+aligned",
            segments=aligned_segments,
        )
    
    def _align_segments_rough(
        self,
        script: ImportedScript,
        transcription: Transcription,
        use_script_text: bool
    ) -> Transcription:
        """
        Alineación aproximada cuando no hay timestamps de palabras.
        
        Distribuye el guion proporcionalmente sobre los segmentos
        de la transcripción.
        """
        if not transcription.segments:
            raise AlignmentError("La transcripción no tiene segmentos")
        
        total_duration = transcription.duration
        script_lines = [l for l in script.lines if l.text.strip()]
        
        if not script_lines:
            raise AlignmentError("El guion está vacío")
        
        # Distribuir proporcionalmente
        duration_per_line = total_duration / len(script_lines)
        
        segments = []
        current_time = 0.0
        
        for line in script_lines:
            segments.append(Segment(
                start=current_time,
                end=current_time + duration_per_line,
                text=line.text if use_script_text else line.text,
                confidence=0.5,  # Baja confianza por ser aproximado
            ))
            current_time += duration_per_line
        
        return Transcription(
            source_file=transcription.source_file,
            language=transcription.language,
            model=f"{transcription.model}+rough-aligned",
            segments=segments,
        )
    
    def _find_closest_segment(
        self,
        segments: List[Segment],
        target_time: float
    ) -> Optional[Segment]:
        """Encuentra el segmento más cercano a un tiempo dado."""
        closest = None
        min_distance = float('inf')
        
        for segment in segments:
            distance = min(
                abs(segment.start - target_time),
                abs(segment.end - target_time)
            )
            if distance < min_distance:
                min_distance = distance
                closest = segment
        
        return closest
    
    def _find_best_match(
        self,
        query_words: List[str],
        trans_words: List[Tuple[Word, int]],
        start_pos: int = 0
    ) -> Tuple[Optional[int], Optional[int], float]:
        """
        Encuentra el mejor match para una secuencia de palabras.
        
        Returns:
            (start_idx, end_idx, confidence) o (None, None, 0.0)
        """
        if not query_words or not trans_words:
            return None, None, 0.0
        
        best_start = None
        best_end = None
        best_score = 0.0
        
        # Buscar en una ventana razonable
        search_end = min(start_pos + len(trans_words), len(trans_words))
        
        for i in range(start_pos, search_end):
            # Intentar match desde esta posición
            match_len = min(len(query_words), len(trans_words) - i)
            
            matches = 0
            for j in range(match_len):
                if i + j < len(trans_words):
                    trans_word = trans_words[i + j][0].text.lower().strip(".,!?;:")
                    query_word = query_words[j].lower().strip(".,!?;:")
                    
                    if trans_word == query_word or self._is_similar(trans_word, query_word):
                        matches += 1
            
            score = matches / len(query_words) if query_words else 0
            
            if score > best_score and score >= self._similarity_threshold:
                best_score = score
                best_start = i
                best_end = i + match_len - 1
        
        return best_start, best_end, best_score
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula la similitud entre dos textos.
        
        Usa una implementación simple basada en palabras comunes.
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _is_similar(self, word1: str, word2: str) -> bool:
        """Verifica si dos palabras son similares."""
        if word1 == word2:
            return True
        
        # Distancia de edición simple
        if abs(len(word1) - len(word2)) > 2:
            return False
        
        # Para palabras cortas, deben ser idénticas
        if len(word1) < 4 or len(word2) < 4:
            return word1 == word2
        
        # Contar caracteres diferentes
        differences = sum(c1 != c2 for c1, c2 in zip(word1, word2))
        max_diff = max(len(word1), len(word2)) * 0.3
        
        return differences <= max_diff
