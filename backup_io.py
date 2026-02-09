from __future__ import annotations

import json
import os
from datetime import datetime

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

BACKUP_EXT = ".jonmem"
ALLOWED_BACKUP_EXTS = (BACKUP_EXT, ".yaml", ".yml")


def ensure_backup_extension(path: str) -> str:
    lower = path.lower()
    if lower.endswith(ALLOWED_BACKUP_EXTS):
        return path
    return f"{path}{BACKUP_EXT}"


def build_backup_payload(vocab: dict, progress: dict, training_log: list, exam_log: list) -> dict:
    return {
        "meta": {"created": datetime.now().isoformat(timespec="seconds")},
        "vocab": vocab,
        "progress": progress,
        "training_log": training_log,
        "exam_log": exam_log,
    }


def normalize_backup_payload(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("invalid backup format")

    vocab = data.get("vocab", {})
    if not isinstance(vocab, dict):
        raise ValueError("invalid vocab data")
    meta = vocab.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    topics = vocab.get("topics", [])
    if not isinstance(topics, list):
        raise ValueError("invalid topics list")
    cards = vocab.get("cards", [])
    if not isinstance(cards, list):
        raise ValueError("invalid cards list")

    progress = data.get("progress", {})
    if not isinstance(progress, dict):
        raise ValueError("invalid progress data")
    training_log = data.get("training_log", [])
    if not isinstance(training_log, list):
        raise ValueError("invalid training log")
    exam_log = data.get("exam_log", [])
    if not isinstance(exam_log, list):
        raise ValueError("invalid exam log")

    return {
        "meta": data.get("meta", {}),
        "vocab": {"meta": meta, "topics": topics, "cards": cards},
        "progress": progress,
        "training_log": training_log,
        "exam_log": exam_log,
    }


def scan_backup_payload(payload: dict) -> dict:
    vocab = payload.get("vocab", {}) if isinstance(payload, dict) else {}
    topics = vocab.get("topics", []) if isinstance(vocab, dict) else []
    cards = vocab.get("cards", []) if isinstance(vocab, dict) else []
    meta = vocab.get("meta", {}) if isinstance(vocab, dict) else {}

    langs = set()
    target_langs = meta.get("target_langs") if isinstance(meta, dict) else None
    if isinstance(target_langs, str):
        langs.add(target_langs)
    elif isinstance(target_langs, list):
        for lang in target_langs:
            if lang:
                langs.add(str(lang))

    for topic in topics if isinstance(topics, list) else []:
        if isinstance(topic, dict):
            lang = topic.get("lang")
            if lang:
                langs.add(str(lang))

    for card in cards if isinstance(cards, list) else []:
        if isinstance(card, dict):
            lang = card.get("lang")
            if lang:
                langs.add(str(lang))

    return {
        "languages": sorted(langs),
        "language_count": len(langs),
        "topic_count": len(topics) if isinstance(topics, list) else 0,
        "card_count": len(cards) if isinstance(cards, list) else 0,
    }


def dump_payload_to_yaml_bytes(payload: dict) -> bytes:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    return text.encode("utf-8")


def load_payload_from_yaml_bytes(raw: bytes) -> dict:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    data = yaml.safe_load(raw.decode("utf-8", errors="replace")) or {}
    if not isinstance(data, dict):
        raise ValueError("invalid yaml structure")
    return data


def load_payload_from_path(path: str) -> dict:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("invalid yaml structure")
    return data


def persist_payload_to_file(path: str, payload: dict) -> None:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)


def persist_payload_to_files(
    payload: dict,
    *,
    vocab_path: str,
    progress_path: str,
    training_log_path: str,
    exam_log_path: str,
    fail_after: str | None = None,
) -> None:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    vocab = payload.get("vocab", {})
    progress = payload.get("progress", {})
    training_log = payload.get("training_log", [])
    exam_log = payload.get("exam_log", [])

    os.makedirs(os.path.dirname(vocab_path), exist_ok=True)
    with open(vocab_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(vocab, handle, sort_keys=False, allow_unicode=True)
    if fail_after == "vocab":
        raise RuntimeError("simulated failure after vocab")

    with open(progress_path, "w", encoding="utf-8") as handle:
        json.dump(progress, handle, ensure_ascii=False, indent=2)
    if fail_after == "progress":
        raise RuntimeError("simulated failure after progress")

    with open(training_log_path, "w", encoding="utf-8") as handle:
        json.dump(training_log, handle, ensure_ascii=False, indent=2)
    if fail_after == "training_log":
        raise RuntimeError("simulated failure after training_log")

    with open(exam_log_path, "w", encoding="utf-8") as handle:
        json.dump(exam_log, handle, ensure_ascii=False, indent=2)
    if fail_after == "exam_log":
        raise RuntimeError("simulated failure after exam_log")


def load_payload_from_files(
    *,
    vocab_path: str,
    progress_path: str,
    training_log_path: str,
    exam_log_path: str,
) -> dict:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    with open(vocab_path, "r", encoding="utf-8", errors="replace") as handle:
        vocab = yaml.safe_load(handle) or {}
    with open(progress_path, "r", encoding="utf-8", errors="replace") as handle:
        progress = json.load(handle)
    with open(training_log_path, "r", encoding="utf-8", errors="replace") as handle:
        training_log = json.load(handle)
    with open(exam_log_path, "r", encoding="utf-8", errors="replace") as handle:
        exam_log = json.load(handle)
    return {
        "vocab": vocab,
        "progress": progress,
        "training_log": training_log,
        "exam_log": exam_log,
    }
