"""Çoklu dil desteği: Türkçe (varsayılan) ve İngilizce.

Anahtar olarak Türkçe metnin kendisi kullanılır. Böylece mevcut kod tabanındaki
metinler `t("...")` ile sarılarak çevrilebilir; `tr` için sözlük gerekmez.
İngilizce karşılığı `app/i18n/en.json` içindedir.
"""
from __future__ import annotations

import json
import locale
from functools import lru_cache
from typing import Any

from . import logger
from .paths import resource_root

SUPPORTED = ("tr", "en")
LANGUAGE_NAMES = {"tr": "Türkçe", "en": "English"}
FLAG = {"tr": "🇹🇷", "en": "🇬🇧"}

_current = "tr"
_catalog: dict[str, str] = {}


# ------------------------------------------------------------------ çeviri
@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, str]:
    path = resource_root() / "app" / "i18n" / "en.json"
    if not path.exists():
        path = resource_root() / "i18n" / "en.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}
    except Exception as exc:  # noqa: BLE001
        logger.warn(f"Çeviri dosyası okunamadı: {exc}")
    return {}


def t(text: str, **kwargs: Any) -> str:
    """Metni aktif dile çevirir. Eksik çeviride Türkçe döner.

    >>> t("Programlar")
    'Programlar'          # dil=tr
    'Programs'            # dil=en

    Biçimlendirme: t("{} seçili", n) veya t("{n} seçili", n=3)
    """
    if not text:
        return text
    result = text
    if _current != "tr":
        result = _load_catalog().get(text, text)
    if kwargs:
        try:
            result = result.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return result


def tn(text: str, n: Any, **kwargs: Any) -> str:
    """Konumsal biçimlendirmeli çeviri: t("{} dosya", 5)"""
    result = t(text, **kwargs)
    try:
        return result.format(n)
    except (IndexError, KeyError, ValueError):
        return result


# --------------------------------------------------------------- dil durumu
def current() -> str:
    return _current


def set_language(code: str) -> bool:
    global _current
    code = (code or "").strip().lower().replace("_", "-")
    if code.startswith("tr"):
        code = "tr"
    elif code.startswith("en"):
        code = "en"
    if code not in SUPPORTED:
        return False
    if code == _current:
        return True
    _current = code
    logger.info(f"Dil değiştirildi: {code}")
    return True


def is_turkish() -> bool:
    return _current == "tr"


def available() -> list[tuple[str, str]]:
    return [(code, LANGUAGE_NAMES[code]) for code in SUPPORTED]


def system_language() -> str:
    """Windows arayüz diline göre varsayılan dil."""
    try:
        import ctypes
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # 0x1F = Türkçe birincil dil kimliği
        if (lang_id & 0x3FF) == 0x1F:
            return "tr"
        return "en"
    except Exception:
        pass
    try:
        code = (locale.getdefaultlocale()[0] or "").lower()
        return "tr" if code.startswith("tr") else "en"
    except Exception:
        return "tr"


def initialize(preferred: str | None = None, fallback_to_system: bool = True) -> str:
    """Dili belirler: açık tercih > Windows dili > Türkçe."""
    _load_catalog()
    if preferred and set_language(preferred):
        return _current
    if fallback_to_system:
        set_language(system_language())
    else:
        set_language("tr")
    return _current


# ------------------------------------------------------- veri dosyası katmanı
def overlay_data(primary: Any, code: str | None = None) -> Any:
    """Veri katmanı uygula (ör. catalog.en.json -> catalog.json üzerine).

    primary: yüklenmiş birincil (Türkçe) veri sözlüğü
    code: dil kodu (varsayılan aktif dil)
    """
    code = code or _current
    if code == "tr" or not isinstance(primary, dict):
        return primary
    name = primary.get("__file__")
    if not name:
        return primary
    return primary


def deep_overlay(base: Any, extra: Any) -> Any:
    """Sözlükleri derin birleştir; listelerde kimlik eşlemesi yap."""
    if isinstance(base, dict) and isinstance(extra, dict):
        out = dict(base)
        for key, value in extra.items():
            if key in out:
                out[key] = deep_overlay(out[key], value)
            else:
                out[key] = value
        return out
    if isinstance(base, list) and isinstance(extra, dict):
        # [{"id":..}] + {"id": {...}} biçimi
        merged = []
        for item in base:
            if isinstance(item, dict) and "id" in item:
                patch = extra.get(str(item["id"]))
                merged.append(deep_overlay(item, patch) if isinstance(patch, dict) else item)
            else:
                merged.append(item)
        return merged
    return extra if extra is not None else base


def load_json_with_overlay(filename: str, code: str | None = None) -> dict:
    """`data/<ad>.json` + gerekiyorsa `data/<ad>.<dil>.json` katmanı."""
    from .paths import data_file

    code = code or _current
    base_path = data_file(filename)
    try:
        base = json.loads(base_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Veri dosyası okunamadı ({filename}): {exc}")
        raise

    if code == "tr":
        return base

    stem, dot, ext = filename.rpartition(".")
    overlay_path = data_file(f"{stem}.{code}.{ext}")
    if not overlay_path.exists():
        return base
    try:
        patch = json.loads(overlay_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warn(f"Çeviri katmanı okunamadı ({overlay_path.name}): {exc}")
        return base
    return deep_overlay(base, patch)
