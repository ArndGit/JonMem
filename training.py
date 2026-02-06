from __future__ import annotations

import random
from typing import Iterable


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return " ".join("".join(ch for ch in text.lower().strip() if ch.isalnum() or ch.isspace()).split())


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


def evaluate_answer(given: str, expected: str) -> bool:
    a = normalize_text(given)
    b = normalize_text(expected)
    if not a or not b:
        return False
    if a == b:
        return True
    dist = levenshtein(a, b)
    if len(b) <= 4:
        return dist == 0
    if len(b) <= 7:
        return dist <= 1
    return dist <= 2


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

