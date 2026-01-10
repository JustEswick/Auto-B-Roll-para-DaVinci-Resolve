"""
Analizador Semántico.

Este módulo analiza el texto transcrito para identificar
conceptos visualizables que pueden representarse con B-Roll.
"""

from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
import logging

from .nlp_processor import NLPProcessor

logger = logging.getLogger(__name__)


@dataclass
class VisualConcept:
    """
    Representa un concepto que puede visualizarse.
    
    Un concepto visualizable es una palabra o frase que puede
    representarse con una imagen o video.
    """
    text: str
    lemma: str  # Forma base de la palabra
    category: str  # noun, verb, entity, etc.
    start_time: float
    end_time: float
    confidence: float = 1.0
    
    # Términos de búsqueda sugeridos
    search_terms: List[str] = field(default_factory=list)
    
    # Contexto circundante
    context: str = ""
    
    @property
    def primary_search_term(self) -> str:
        """Retorna el término de búsqueda principal."""
        return self.search_terms[0] if self.search_terms else self.text


@dataclass
class AnalysisResult:
    """Resultado del análisis semántico."""
    concepts: List[VisualConcept]
    total_words: int
    visual_density: float  # Ratio de conceptos visualizables
    language: str
    
    def get_concepts_in_range(
        self, 
        start: float, 
        end: float
    ) -> List[VisualConcept]:
        """Obtiene conceptos en un rango de tiempo."""
        return [
            c for c in self.concepts
            if c.start_time < end and c.end_time > start
        ]
    
    def get_unique_search_terms(self) -> List[str]:
        """
        Obtiene términos de búsqueda únicos y limpios.
        
        Filtra términos de baja calidad como comas, números solos,
        palabras muy cortas, etc.
        """
        terms = set()
        
        # Solo usar el término principal de cada concepto (el primero)
        for concept in self.concepts:
            if concept.search_terms:
                term = concept.search_terms[0]
                # Limpiar el término
                term = self._clean_search_term(term)
                if term:
                    terms.add(term)
        
        return sorted(terms)
    
    def _clean_search_term(self, term: str) -> str:
        """Limpia y valida un término de búsqueda."""
        if not term:
            return ""
        
        # Quitar espacios y comas al inicio/final
        term = term.strip().strip(',').strip()
        
        # Ignorar si es muy corto
        if len(term) < 3:
            return ""
        
        # Ignorar si es solo números
        if term.isdigit():
            return ""
        
        # Ignorar si empieza con coma o puntuación
        if term[0] in ',.:;!?':
            term = term[1:].strip()
            if len(term) < 3:
                return ""
        
        # Ignorar palabras comunes no visualizables
        stopwords = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 
                     'de', 'del', 'en', 'y', 'o', 'a', 'que', 'es', 'por',
                     'para', 'con', 'sin', 'sobre', 'the', 'a', 'an', 'and'}
        if term.lower() in stopwords:
            return ""
        
        return term


class SemanticAnalyzer:
    """
    Analizador semántico para extracción de conceptos visualizables.
    
    Utiliza NLP (spaCy) para identificar sustantivos, entidades y
    conceptos que pueden representarse visualmente.
    """
    
    # Categorías de entidades que son visualizables
    VISUAL_ENTITY_TYPES = {
        "PER": "persona",      # Personas
        "LOC": "lugar",        # Ubicaciones
        "ORG": "organización", # Organizaciones
        "MISC": "concepto",    # Otros
        "GPE": "lugar",        # Entidades geopolíticas
        "FAC": "edificio",     # Edificios/instalaciones
        "PRODUCT": "producto", # Productos
    }
    
    # POS tags que indican conceptos visualizables
    VISUAL_POS_TAGS = {"NOUN", "PROPN"}
    
    # Palabras a ignorar (stop words adicionales para B-Roll)
    IGNORE_WORDS = {
        "cosa", "cosas", "vez", "veces", "forma", "manera",
        "tipo", "tipos", "parte", "partes", "algo", "nada",
        "todo", "mucho", "poco", "más", "menos", "muy",
        "thing", "things", "way", "time", "part", "something",
    }
    
    def __init__(self, language: str = "es"):
        """
        Inicializa el analizador.
        
        Args:
            language: Código de idioma ('es' o 'en')
        """
        self._language = language
        self._nlp = NLPProcessor(language)
    
    def analyze(
        self,
        text: str,
        timestamps: Optional[List[Tuple[float, float, str]]] = None
    ) -> AnalysisResult:
        """
        Analiza texto para extraer conceptos visualizables.
        
        Args:
            text: Texto a analizar
            timestamps: Lista opcional de (start, end, text) para fragmentos
            
        Returns:
            Resultado del análisis con conceptos extraídos
        """
        logger.info("Iniciando análisis semántico...")
        
        if timestamps:
            concepts = self._analyze_with_timestamps(timestamps)
        else:
            concepts = self._analyze_text(text, 0.0, len(text.split()) * 0.5)
        
        # Filtrar y deduplicar
        concepts = self._filter_concepts(concepts)
        concepts = self._deduplicate_concepts(concepts)
        
        # Enriquecer con términos de búsqueda
        concepts = self._enrich_search_terms(concepts)
        
        total_words = len(text.split())
        visual_density = len(concepts) / total_words if total_words > 0 else 0
        
        logger.info(
            f"Análisis completado: {len(concepts)} conceptos visualizables "
            f"de {total_words} palabras (densidad: {visual_density:.2%})"
        )
        
        return AnalysisResult(
            concepts=concepts,
            total_words=total_words,
            visual_density=visual_density,
            language=self._language,
        )
    
    def _analyze_with_timestamps(
        self,
        timestamps: List[Tuple[float, float, str]]
    ) -> List[VisualConcept]:
        """Analiza fragmentos con timestamps."""
        all_concepts = []
        
        for start, end, text in timestamps:
            concepts = self._analyze_text(text, start, end)
            all_concepts.extend(concepts)
        
        return all_concepts
    
    def _analyze_text(
        self,
        text: str,
        start_time: float,
        end_time: float
    ) -> List[VisualConcept]:
        """Analiza un fragmento de texto."""
        concepts = []
        
        # Procesar con NLP
        doc = self._nlp.process(text)
        
        # Extraer entidades nombradas
        for ent in doc.ents:
            if ent.label_ in self.VISUAL_ENTITY_TYPES:
                concept = VisualConcept(
                    text=ent.text,
                    lemma=ent.text.lower(),
                    category=self.VISUAL_ENTITY_TYPES.get(ent.label_, "concepto"),
                    start_time=start_time,
                    end_time=end_time,
                    confidence=0.9,
                    context=text,
                )
                concepts.append(concept)
        
        # Extraer sustantivos relevantes
        for token in doc:
            if token.pos_ in self.VISUAL_POS_TAGS:
                if self._is_visualizable(token):
                    concept = VisualConcept(
                        text=token.text,
                        lemma=token.lemma_.lower(),
                        category="noun" if token.pos_ == "NOUN" else "proper_noun",
                        start_time=start_time,
                        end_time=end_time,
                        confidence=0.7,
                        context=text,
                    )
                    concepts.append(concept)
        
        # Extraer chunks nominales (noun phrases)
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) >= 2:
                concept = VisualConcept(
                    text=chunk.text,
                    lemma=chunk.root.lemma_.lower(),
                    category="noun_phrase",
                    start_time=start_time,
                    end_time=end_time,
                    confidence=0.8,
                    context=text,
                )
                concepts.append(concept)
        
        return concepts
    
    def _is_visualizable(self, token) -> bool:
        """Determina si un token es visualizable."""
        # Ignorar palabras muy cortas
        if len(token.text) < 3:
            return False
        
        # Ignorar palabras en la lista de ignorados
        if token.lemma_.lower() in self.IGNORE_WORDS:
            return False
        
        # Ignorar pronombres que a veces se detectan como sustantivos
        if token.pos_ == "PRON":
            return False
        
        return True
    
    def _filter_concepts(
        self,
        concepts: List[VisualConcept]
    ) -> List[VisualConcept]:
        """Filtra conceptos de baja calidad."""
        filtered = []
        
        for concept in concepts:
            # Filtrar por longitud mínima
            if len(concept.text) < 3:
                continue
            
            # Filtrar palabras ignoradas
            if concept.lemma in self.IGNORE_WORDS:
                continue
            
            filtered.append(concept)
        
        return filtered
    
    def _deduplicate_concepts(
        self,
        concepts: List[VisualConcept]
    ) -> List[VisualConcept]:
        """Elimina conceptos duplicados."""
        seen_lemmas: Dict[str, VisualConcept] = {}
        
        for concept in concepts:
            key = f"{concept.lemma}_{concept.start_time:.1f}"
            
            if key not in seen_lemmas:
                seen_lemmas[key] = concept
            elif concept.confidence > seen_lemmas[key].confidence:
                seen_lemmas[key] = concept
        
        return list(seen_lemmas.values())
    
    def _enrich_search_terms(
        self,
        concepts: List[VisualConcept]
    ) -> List[VisualConcept]:
        """
        Enriquece conceptos con términos de búsqueda alternativos.
        
        Solo agrega el texto original, lemma y traducción al inglés.
        NO agrega palabras individuales de frases para evitar ruido.
        """
        for concept in concepts:
            terms = []
            
            # Limpiar el texto original antes de añadir
            clean_text = concept.text.strip().strip(',').strip()
            if clean_text and len(clean_text) >= 3:
                terms.append(clean_text)
            
            # Agregar lemma si es diferente y válido
            clean_lemma = concept.lemma.strip().strip(',').strip()
            if clean_lemma and len(clean_lemma) >= 3 and clean_lemma != clean_text.lower():
                terms.append(clean_lemma)
            
            # Agregar traducción al inglés si es español (útil para APIs)
            if self._language == "es" and clean_lemma:
                english_term = self._nlp.translate_term(clean_lemma)
                if english_term and english_term != clean_lemma and len(english_term) >= 3:
                    terms.append(english_term)
            
            # Mantener orden, eliminar duplicados
            concept.search_terms = list(dict.fromkeys(terms))
        
        return concepts
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extrae las keywords más relevantes de un texto.
        
        Args:
            text: Texto a analizar
            top_n: Número máximo de keywords
            
        Returns:
            Lista de keywords ordenadas por relevancia
        """
        result = self.analyze(text)
        
        # Contar frecuencia de lemmas
        freq: Dict[str, int] = {}
        for concept in result.concepts:
            freq[concept.lemma] = freq.get(concept.lemma, 0) + 1
        
        # Ordenar por frecuencia
        sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        
        return [kw for kw, _ in sorted_keywords[:top_n]]
