import copy

import training


class StaticRng:
    def shuffle(self, _items):
        return None

    def random(self):
        return 0.0


def _make_card(card_id: str, *, lang: str = "en", topic: str = "t1") -> dict:
    return {
        "id": card_id,
        "lang": lang,
        "topic": topic,
        "de": f"de_{card_id}",
        "en": f"en_{card_id}",
    }


def _simulate_progress(items: list[dict], answers: list[bool], progress: dict,
                       *, direction: str = "de_to_en", max_stage: int = 4) -> dict:
    progress = copy.deepcopy(progress)
    for item, correct in zip(items, answers):
        card_id = item["id"]
        entry = progress.setdefault(card_id, {})
        dir_entry = entry.setdefault(direction, {"stage": int(item.get("stage", 1) or 1)})
        stage = int(dir_entry.get("stage", 1))
        new_stage = training.compute_next_stage(stage, bool(correct), max_stage)
        dir_entry["stage"] = new_stage
    return progress


def test_introduce_session_simulation():
    cards = [_make_card(f"c{i}") for i in range(1, 5)]
    rng = StaticRng()
    items = training.build_session_items(
        cards,
        {},
        mode="introduce",
        direction="de_to_en",
        lang="en",
        topic_filter_enabled=False,
        topic_filter=set(),
        max_items=8,
        introduce_repeat_count=2,
        max_stage=4,
        pyramid_stage_weights={1: 4, 2: 3, 3: 2, 4: 1},
        rng=rng,
    )

    assert [item["id"] for item in items] == ["c1", "c2", "c3", "c4", "c1", "c2", "c3", "c4"]

    answers = [True, False, True, False, False, True, True, False]
    updated = _simulate_progress(items, answers, {}, direction="de_to_en", max_stage=4)
    stages = {cid: updated[cid]["de_to_en"]["stage"] for cid in ("c1", "c2", "c3", "c4")}
    assert stages == {"c1": 1, "c2": 2, "c3": 3, "c4": 1}


def test_review_session_simulation_no_duplicates():
    cards = [
        _make_card("s1"),
        _make_card("s2"),
        _make_card("s3"),
        _make_card("s4"),
    ]
    progress = {
        "s1": {"de_to_en": {"stage": 1}},
        "s2": {"de_to_en": {"stage": 2}},
        "s3": {"de_to_en": {"stage": 3}},
        "s4": {"de_to_en": {"stage": 4}},
    }
    rng = StaticRng()
    items = training.build_session_items(
        cards,
        progress,
        mode="review",
        direction="de_to_en",
        lang="en",
        topic_filter_enabled=False,
        topic_filter=set(),
        max_items=4,
        introduce_repeat_count=2,
        max_stage=4,
        pyramid_stage_weights={1: 4, 2: 3, 3: 2, 4: 1},
        rng=rng,
    )

    ids = [item["id"] for item in items]
    assert ids == ["s1", "s2", "s3", "s4"]
    assert len(set(ids)) == len(ids)

    answers = [True, False, False, True]
    updated = _simulate_progress(items, answers, progress, direction="de_to_en", max_stage=4)
    stages = {cid: updated[cid]["de_to_en"]["stage"] for cid in ("s1", "s2", "s3", "s4")}
    assert stages == {"s1": 2, "s2": 1, "s3": 2, "s4": 4}


def test_exam_session_simulation():
    cards = [_make_card(f"e{i}", topic="t2") for i in range(1, 4)]
    items = [
        {"id": c["id"], "prompt": c["de"], "answer": c["en"]}
        for c in cards
    ]
    answers = ["en_e1", "wrong", "en_e3"]

    exam_total = 0
    exam_correct = 0
    exam_wrong = []
    for item, given in zip(items, answers):
        expected = item["answer"]
        correct = training.strict_match(given, expected)
        exam_total += 1
        if correct:
            exam_correct += 1
        else:
            exam_wrong.append({
                "prompt": item["prompt"],
                "given": given,
                "correct": expected,
            })

    assert exam_total == 3
    assert exam_correct == 2
    assert exam_wrong == [{
        "prompt": "de_e2",
        "given": "wrong",
        "correct": "en_e2",
    }]
