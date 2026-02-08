import pytest

import backup_io


def _make_payload():
    vocab = {
        "meta": {"target_langs": ["en", "es"]},
        "topics": [{"id": "t1", "lang": "en", "name": "Basics"}],
        "cards": [{"id": "c1", "lang": "en", "topic": "t1", "de": "Haus", "en": "house"}],
    }
    progress = {"c1": {"de_to_en": {"stage": 2}}}
    training_log = [{"mode": "review", "started": "2026-02-01T10:00:00"}]
    exam_log = [{"grade": 1, "started": "2026-02-01T11:00:00"}]
    return backup_io.build_backup_payload(vocab, progress, training_log, exam_log)


def test_backup_export_import_roundtrip():
    payload = _make_payload()
    raw = backup_io.dump_payload_to_yaml_bytes(payload)
    loaded = backup_io.load_payload_from_yaml_bytes(raw)
    normalized = backup_io.normalize_backup_payload(loaded)
    assert normalized["vocab"] == payload["vocab"]
    assert normalized["progress"] == payload["progress"]
    assert normalized["training_log"] == payload["training_log"]
    assert normalized["exam_log"] == payload["exam_log"]


def test_scan_backup_payload_counts():
    payload = _make_payload()
    scan = backup_io.scan_backup_payload(payload)
    assert scan["language_count"] == 2
    assert scan["topic_count"] == 1
    assert scan["card_count"] == 1
    assert scan["languages"] == ["en", "es"]


def test_ensure_backup_extension():
    assert backup_io.ensure_backup_extension("backup") == f"backup{backup_io.BACKUP_EXT}"
    assert backup_io.ensure_backup_extension("backup.yaml") == "backup.yaml"
    assert backup_io.ensure_backup_extension(f"backup{backup_io.BACKUP_EXT}") == f"backup{backup_io.BACKUP_EXT}"


def test_rollback_restore_after_failed_persist(tmp_path):
    old_payload = _make_payload()
    new_payload = _make_payload()
    new_payload["vocab"]["topics"].append({"id": "t2", "lang": "es", "name": "Extra"})

    vocab_path = tmp_path / "vocab.yaml"
    progress_path = tmp_path / "progress.json"
    training_log_path = tmp_path / "training_log.json"
    exam_log_path = tmp_path / "exam_log.json"

    backup_io.persist_payload_to_files(
        old_payload,
        vocab_path=str(vocab_path),
        progress_path=str(progress_path),
        training_log_path=str(training_log_path),
        exam_log_path=str(exam_log_path),
    )

    with pytest.raises(RuntimeError):
        backup_io.persist_payload_to_files(
            new_payload,
            vocab_path=str(vocab_path),
            progress_path=str(progress_path),
            training_log_path=str(training_log_path),
            exam_log_path=str(exam_log_path),
            fail_after="progress",
        )

    backup_io.persist_payload_to_files(
        old_payload,
        vocab_path=str(vocab_path),
        progress_path=str(progress_path),
        training_log_path=str(training_log_path),
        exam_log_path=str(exam_log_path),
    )

    restored = backup_io.load_payload_from_files(
        vocab_path=str(vocab_path),
        progress_path=str(progress_path),
        training_log_path=str(training_log_path),
        exam_log_path=str(exam_log_path),
    )
    assert restored["vocab"] == old_payload["vocab"]
    assert restored["progress"] == old_payload["progress"]
    assert restored["training_log"] == old_payload["training_log"]
    assert restored["exam_log"] == old_payload["exam_log"]
