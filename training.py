from __future__ import annotations

import random
import unicodedata
from typing import Iterable


def normalize_spaces(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return " ".join(text.strip().split())


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = normalize_spaces(text)
    return " ".join("".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).split())


def _is_punct(ch: str) -> bool:
    return unicodedata.category(ch).startswith("P")


def _strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")


def _letters_only(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum())


def strict_match(given: str, expected: str) -> bool:
    if not isinstance(given, str) or not isinstance(expected, str):
        return False
    return normalize_spaces(given) == normalize_spaces(expected)


def list_unseen_cards(cards: Iterable[dict], progress: dict, *, direction: str, lang: str) -> list[dict]:
    unseen = []
    for card in cards:
        if card.get("lang", "en") != lang:
            continue
        card_id = card.get("id")
        if not card_id:
            continue
        if progress.get(card_id, {}).get(direction) is None:
            unseen.append(card)
    return unseen


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def analyze_answer(given: str, expected: str) -> dict:
    given_norm = normalize_spaces(given)
    expected_norm = normalize_spaces(expected)
    if not given_norm or not expected_norm:
        return {
            "correct": False,
            "given_norm": given_norm,
            "expected_norm": expected_norm,
            "case_only": False,
            "letter_errors": 0,
            "accent_errors": 0,
            "punct_errors": 0,
            "missing_word": False,
        }

    correct = given_norm == expected_norm
    given_case = given_norm.casefold()
    expected_case = expected_norm.casefold()
    case_only = (given_case == expected_case) and not correct

    given_letters = _letters_only(_strip_accents(given_case))
    expected_letters = _letters_only(_strip_accents(expected_case))
    letter_errors = levenshtein(given_letters, expected_letters)

    accent_errors = 0
    if _strip_accents(given_case) == _strip_accents(expected_case) and given_case != expected_case:
        if len(given_case) == len(expected_case):
            for gch, ech in zip(given_case, expected_case):
                if gch == ech:
                    continue
                if _strip_accents(gch) == _strip_accents(ech) and gch.isalpha() and ech.isalpha():
                    accent_errors += 1
        else:
            accent_errors = levenshtein(_strip_accents(given_case), given_case)

    given_punct = "".join(ch for ch in given_norm if _is_punct(ch))
    expected_punct = "".join(ch for ch in expected_norm if _is_punct(ch))
    punct_errors = levenshtein(given_punct, expected_punct)

    given_words = [w for w in given_norm.split(" ") if w]
    expected_words = [w for w in expected_norm.split(" ") if w]
    missing_word = len(given_words) < len(expected_words)

    return {
        "correct": correct,
        "given_norm": given_norm,
        "expected_norm": expected_norm,
        "case_only": case_only,
        "letter_errors": letter_errors,
        "accent_errors": accent_errors,
        "punct_errors": punct_errors,
        "missing_word": missing_word,
    }


def evaluate_answer(given: str, expected: str) -> bool:
    return strict_match(given, expected)


def shuffle_avoid_adjacent(items: list[dict], key: str, rng: random.Random | None = None,
                           attempts: int = 200) -> list[dict]:
    if len(items) < 3:
        return items
    rng = rng or random
    for _ in range(attempts):
        rng.shuffle(items)
        if all(items[i].get(key) != items[i - 1].get(key) for i in range(1, len(items))):
            return items
    return items


def compute_next_stage(stage: int, correct: bool, max_stage: int) -> int:
    stage = int(stage or 1)
    if correct:
        return min(max_stage, stage + 1)
    return max(1, stage - 1)


def build_session_items(
    cards: Iterable[dict],
    progress: dict,
    *,
    mode: str,
    direction: str,
    lang: str,
    topic_filter_enabled: bool,
    topic_filter: set[str],
    max_items: int,
    introduce_repeat_count: int,
    max_stage: int,
    pyramid_stage_weights: dict[int, int],
    rng: random.Random | None = None,
) -> list[dict]:
    rng = rng or random
    items = []
    for card in cards:
        card_id = card.get("id")
        if not card_id:
            continue
        if card.get("lang", "en") != lang:
            continue
        prog = progress.get(card_id, {}).get(direction)
        if mode == "introduce" and prog is not None:
            continue
        if mode == "review" and prog is None:
            continue
        if mode == "review" and topic_filter_enabled:
            if card.get("topic") not in topic_filter:
                continue
        stage = 1
        if prog is not None:
            stage = int(prog.get("stage", 1))
        items.append({
            "id": card_id,
            "prompt": card.get("de") if direction == "de_to_en" else card.get("en"),
            "answer": card.get("en") if direction == "de_to_en" else card.get("de"),
            "hint": card.get("hint_de_to_en") if direction == "de_to_en" else card.get("hint_en_to_de"),
            "de": card.get("de", ""),
            "en": card.get("en", ""),
            "hint_de_to_en": card.get("hint_de_to_en", ""),
            "hint_en_to_de": card.get("hint_en_to_de", ""),
            "stage": stage,
            "topic": card.get("topic"),
            "lang": card.get("lang", "en"),
        })

    if mode == "introduce":
        rng.shuffle(items)
        unique_limit = max(1, max_items // max(1, introduce_repeat_count))
        items = items[:unique_limit]
        session = items * max(1, introduce_repeat_count)
        return shuffle_avoid_adjacent(session, "id", rng)[:max_items]

    if mode == "review":
        stage_pools: dict[int, list[dict]] = {stage: [] for stage in range(1, max_stage + 1)}
        for item in items:
            stage_pools.get(item.get("stage", 1), stage_pools[1]).append(item)
        for pool in stage_pools.values():
            rng.shuffle(pool)

        weight_pattern = []
        for stage in range(1, max_stage + 1):
            weight = pyramid_stage_weights.get(stage, 1)
            weight_pattern.extend([stage] * max(1, weight))

        session: list[dict] = []
        while len(session) < max_items:
            added_any = False
            for stage in weight_pattern:
                if len(session) >= max_items:
                    break
                pool = stage_pools.get(stage)
                if pool:
                    session.append(pool.pop())
                    added_any = True
            if not added_any:
                break
        rng.shuffle(session)
        return session

    rng.shuffle(items)
    return items[:max_items]

