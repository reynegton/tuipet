"""
Localization engine for TuiPet.
Handles dynamic loading of translation dictionaries (JSON) and provides
string translation functions (t, t_col) with fallback support.
"""
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import json
import os
import logging
from typing import Dict, Any

# Current language state
_current_language: str = "en"
_translations: Dict[str, Dict[str, str]] = {}
_fallback_language: str = "en"

_HERE: str = os.path.dirname(os.path.abspath(__file__))
_LOCALES_DIR: str = os.path.join(_HERE, "locales")

def set_language(lang_code: str) -> None:
    """Sets the active language and loads the dictionary if not loaded yet."""
    global _current_language
    
    if not os.path.exists(_LOCALES_DIR):
        logging.warning(f"Locales directory not found at {_LOCALES_DIR}")
        return

    _current_language = lang_code
    
    # Preload the target language
    if lang_code not in _translations:
        _load_language(lang_code)
    
    # Always ensure fallback is loaded
    if _fallback_language not in _translations:
        _load_language(_fallback_language)

def get_language() -> str:
    """Returns the current language code."""
    return _current_language

def _load_language(lang_code: str) -> None:
    """Loads a JSON file into the translation memory."""
    filepath: str = os.path.join(_LOCALES_DIR, f"{lang_code}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                _translations[lang_code] = json.load(f)
        except Exception as e:
            logging.error(f"Failed to load language {lang_code}: {e}")
            _translations[lang_code] = {}
    else:
        # If the file doesn't exist yet, we just create an empty dictionary
        _translations[lang_code] = {}

def t(key: str, fallback: str | None = None, **kwargs: Any) -> str:
    """
    Translates a key into the current language.
    If the key is not found in the current language, falls back to English.
    If not found in English, returns the fallback string if provided, otherwise the key itself.
    """
    lang_dict: Dict[str, str] = _translations.get(_current_language, {})
    
    text: str | None = lang_dict.get(key)
    
    if text is None:
        fallback_dict: Dict[str, str] = _translations.get(_fallback_language, {})
        text = fallback_dict.get(key)
        
    if text is None:
        text = fallback if fallback is not None else key
        
    # Apply f-string style string formatting if kwargs are provided
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError as e:
            logging.warning(f"Missing translation format key {e} in '{key}'")
            return text
            
    return text

def t_col(row: Dict[str, Any], field: str) -> str:
    """Extracts a localized column from a CSV row (e.g. Name_pt)."""
    lang = _current_language
    col = f"{field}_{lang}" if lang != "en" else field
    return str(row.get(col) or row.get(field) or "")
