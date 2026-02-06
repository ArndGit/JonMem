import training


def _make_card(card_id: str, *, lang: str, topic: str) -> dict:
    return {
        "id": card_id,
        "lang": lang,
        "topic": topic,
        "de": f"de_{card_id}",
        "en": f"en_{card_id}",
    }


def test_list_unseen_cards_preserves_order():
    cards = [_make_card(f"c{i}", lang="en", topic="t1") for i in range(6)]
    progress = {"c1": {"de_to_en": {"stage": 1}}, "c3": {"de_to_en": {"stage": 2}}}
    unseen = training.list_unseen_cards(cards, progress, direction="de_to_en", lang="en")
    assert [c["id"] for c in unseen] == ["c0", "c2", "c4", "c5"]


def test_review_pyramid_weights():
    cards = []
    progress = {}
    for stage in range(1, 5):
        for i in range(5):
            card_id = f"s{stage}_{i}"
            cards.append(_make_card(card_id, lang="en", topic="t1"))
            progress[card_id] = {"de_to_en": {"stage": stage}}
    rng = random.Random(7)
    items = training.build_session_items(
        cards,
        progress,
        mode="review",
        direction="de_to_en",
        lang="en",
        topic_filter_enabled=False,
        topic_filter=set(),
        max_items=10,
        introduce_repeat_count=2,
        max_stage=4,
        pyramid_stage_weights={1: 4, 2: 3, 3: 2, 4: 1},
        rng=rng,
    )
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for item in items:
        counts[item["stage"]] += 1
    assert counts == {1: 4, 2: 3, 3: 2, 4: 1}


def test_review_topic_filter():
    cards = [
        _make_card("a1", lang="en", topic="t1"),
        _make_card("a2", lang="en", topic="t2"),
    ]
    progress = {
        "a1": {"de_to_en": {"stage": 2}},
        "a2": {"de_to_en": {"stage": 2}},
    }
    items = training.build_session_items(
        cards,
        progress,
        mode="review",
        direction="de_to_en",
        lang="en",
        topic_filter_enabled=True,
        topic_filter={"t2"},
        max_items=10,
        introduce_repeat_count=2,
        max_stage=4,
        pyramid_stage_weights={1: 4, 2: 3, 3: 2, 4: 1},
    )
    assert len(items) == 1
    assert items[0]["id"] == "a2"


def test_compute_next_stage():
    assert training.compute_next_stage(1, True, 4) == 2
    assert training.compute_next_stage(4, True, 4) == 4
    assert training.compute_next_stage(3, False, 4) == 2
    assert training.compute_next_stage(1, False, 4) == 1


def test_evaluate_answer_spanish_unicode():
    assert training.evaluate_answer("la maleta", "la maleta") is True
    assert training.evaluate_answer("la  maleta", "la maleta") is True
    assert training.evaluate_answer("la maleta", "la maleta ") is True
    assert training.evaluate_answer("la maleta", None) is False


def test_analyze_answer_case_only():
    analysis = training.analyze_answer("Haus", "haus")
    assert analysis["correct"] is False
    assert analysis["case_only"] is True
    assert analysis["letter_errors"] == 0


def test_analyze_answer_accents_and_punct():
    analysis = training.analyze_answer("nino", "niño")
    assert analysis["correct"] is False
    assert analysis["accent_errors"] >= 1

    analysis = training.analyze_answer("lami", "l'ami")
    assert analysis["punct_errors"] >= 1
