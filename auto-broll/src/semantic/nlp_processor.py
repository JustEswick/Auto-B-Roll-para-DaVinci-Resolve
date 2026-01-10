"""
Procesador NLP con spaCy.

Este módulo encapsula la funcionalidad de procesamiento
de lenguaje natural usando spaCy.
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


# Traducciones básicas español -> inglés para búsqueda
ES_EN_TRANSLATIONS = {
    # Tecnología
    "computadora": "computer",
    "ordenador": "computer",
    "teléfono": "phone",
    "celular": "cellphone",
    "móvil": "mobile phone",
    "pantalla": "screen",
    "teclado": "keyboard",
    "ratón": "mouse",
    "código": "code",
    "programación": "programming",
    "inteligencia artificial": "artificial intelligence",
    "robot": "robot",
    "internet": "internet",
    "red": "network",
    "nube": "cloud",
    "servidor": "server",
    "datos": "data",
    "software": "software",
    "aplicación": "application",
    
    # Negocios
    "oficina": "office",
    "reunión": "meeting",
    "empresa": "company",
    "negocio": "business",
    "trabajo": "work",
    "equipo": "team",
    "proyecto": "project",
    "cliente": "client",
    "dinero": "money",
    "inversión": "investment",
    "mercado": "market",
    "ventas": "sales",
    "marketing": "marketing",
    
    # Creatividad
    "video": "video",
    "cámara": "camera",
    "fotografía": "photography",
    "película": "movie",
    "música": "music",
    "arte": "art",
    "diseño": "design",
    "creativo": "creative",
    "edición": "editing",
    
    # Naturaleza
    "naturaleza": "nature",
    "montaña": "mountain",
    "playa": "beach",
    "mar": "sea",
    "océano": "ocean",
    "bosque": "forest",
    "árbol": "tree",
    "flor": "flower",
    "animal": "animal",
    "cielo": "sky",
    "sol": "sun",
    "luna": "moon",
    
    # Personas
    "persona": "person",
    "gente": "people",
    "hombre": "man",
    "mujer": "woman",
    "niño": "child",
    "familia": "family",
    "amigo": "friend",
    
    # Lugares
    "ciudad": "city",
    "país": "country",
    "casa": "house",
    "edificio": "building",
    "calle": "street",
    "parque": "park",
    "restaurante": "restaurant",
    "tienda": "store",
    
    # Acciones (para contexto)
    "hablar": "speaking",
    "caminar": "walking",
    "correr": "running",
    "escribir": "writing",
    "leer": "reading",
    "pensar": "thinking",
    "trabajar": "working",
    "crear": "creating",
}


class NLPProcessor:
    """
    Procesador de lenguaje natural con spaCy.
    
    Maneja la carga del modelo y proporciona métodos de alto nivel
    para procesamiento de texto.
    """
    
    MODEL_NAMES = {
        "es": "es_core_news_sm",
        "en": "en_core_web_sm",
    }
    
    def __init__(self, language: str = "es"):
        """
        Inicializa el procesador.
        
        Args:
            language: Código de idioma ('es' o 'en')
        """
        self._language = language
        self._nlp = None
        self._loaded = False
    
    def _ensure_loaded(self) -> None:
        """Carga el modelo si no está cargado."""
        if self._loaded:
            return
        
        model_name = self.MODEL_NAMES.get(self._language)
        if not model_name:
            raise ValueError(f"Idioma no soportado: {self._language}")
        
        try:
            import spacy
            
            logger.info(f"Cargando modelo spaCy: {model_name}")
            self._nlp = spacy.load(model_name)
            self._loaded = True
            logger.info(f"Modelo spaCy cargado: {model_name}")
            
        except OSError:
            logger.warning(
                f"Modelo {model_name} no encontrado. "
                f"Descargando con: python -m spacy download {model_name}"
            )
            raise RuntimeError(
                f"Modelo spaCy '{model_name}' no está instalado.\n"
                f"Instálalo con: python -m spacy download {model_name}"
            )
    
    def process(self, text: str) -> Any:
        """
        Procesa texto con spaCy.
        
        Args:
            text: Texto a procesar
            
        Returns:
            Documento spaCy procesado
        """
        self._ensure_loaded()
        return self._nlp(text)
    
    def extract_entities(self, text: str) -> list:
        """
        Extrae entidades nombradas del texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Lista de tuplas (texto, etiqueta)
        """
        doc = self.process(text)
        return [(ent.text, ent.label_) for ent in doc.ents]
    
    def extract_nouns(self, text: str) -> list:
        """
        Extrae sustantivos del texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Lista de sustantivos (texto, lemma)
        """
        doc = self.process(text)
        return [
            (token.text, token.lemma_)
            for token in doc
            if token.pos_ in ("NOUN", "PROPN")
        ]
    
    def extract_noun_chunks(self, text: str) -> list:
        """
        Extrae frases nominales del texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Lista de frases nominales
        """
        doc = self.process(text)
        return [chunk.text for chunk in doc.noun_chunks]
    
    def get_summary_stats(self, text: str) -> Dict[str, int]:
        """
        Obtiene estadísticas del texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Diccionario con estadísticas
        """
        doc = self.process(text)
        
        pos_counts: Dict[str, int] = {}
        for token in doc:
            pos_counts[token.pos_] = pos_counts.get(token.pos_, 0) + 1
        
        return {
            "tokens": len(doc),
            "sentences": len(list(doc.sents)),
            "entities": len(doc.ents),
            "noun_chunks": len(list(doc.noun_chunks)),
            "nouns": pos_counts.get("NOUN", 0),
            "verbs": pos_counts.get("VERB", 0),
            "adjectives": pos_counts.get("ADJ", 0),
        }
    
    def translate_term(self, term: str) -> Optional[str]:
        """
        Traduce un término de español a inglés.
        
        Usa un diccionario de traducciones comunes.
        
        Args:
            term: Término en español
            
        Returns:
            Traducción en inglés o None
        """
        if self._language != "es":
            return None
        
        term_lower = term.lower()
        return ES_EN_TRANSLATIONS.get(term_lower)
    
    @property
    def is_loaded(self) -> bool:
        """Indica si el modelo está cargado."""
        return self._loaded
    
    @property
    def language(self) -> str:
        """Idioma del procesador."""
        return self._language
