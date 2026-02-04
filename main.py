# Copyright (C) 2026 Arnd Brandes.
# Dieses Programm kann durch jedermann gemaess den Bestimmungen der Deutschen Freien Software Lizenz genutzt werden.

from __future__ import annotations

import calendar
import json
import math
import os
import random
import struct
import traceback
import wave
from datetime import datetime, timedelta

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import platform as kivy_platform

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

try:
    from plyer import notification  # type: ignore
except Exception:
    notification = None

__version__ = "0.1"

IS_ANDROID = (kivy_platform == "android")

SEED_VOCAB_PATH = os.path.join(os.path.dirname(__file__), "data", "seed_vocab.yaml")

SESSION_MAX_ITEMS = 10
SESSION_SECONDS = 300
MAX_STAGE = 4

SUPPORT_URL = "https://www.paypal.com/donate/?hosted_button_id=PND6Y8CGNZVW6"


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _load_yaml(path: str) -> dict:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("invalid yaml structure")
    return data


def _save_yaml(path: str, data: dict) -> None:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return json.load(handle)


def _save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def _slugify(text: str) -> str:
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("_")
    slug = "".join(out).strip("_")
    return slug or "topic"


def _normalize(text: str) -> str:
    return " ".join("".join(ch for ch in text.lower().strip() if ch.isalnum() or ch.isspace()).split())


def _levenshtein(a: str, b: str) -> int:
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


def _ensure_beep(path: str) -> None:
    if os.path.exists(path):
        return
    framerate = 44100
    duration = 0.12
    freq = 880.0
    samples = int(framerate * duration)
    with wave.open(path, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        for i in range(samples):
            val = int(32767 * 0.5 * math.sin(2 * math.pi * freq * (i / framerate)))
            wav.writeframes(struct.pack("<h", val))


class TopBar(BoxLayout):
    def __init__(self, app, title: str, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=48, **kwargs)
        self.app = app
        self.add_widget(Button(text="≡", size_hint_x=None, width=48, on_release=self.app.open_menu))
        self.add_widget(Label(text=title))


class MenuScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(TopBar(app, "JonMem"))
        body = BoxLayout(orientation="vertical", padding=16, spacing=12)
        body.add_widget(Button(text="Training starten", on_release=lambda *_: app.show_training_setup()))
        body.add_widget(Button(text="Vokabeln eingeben", on_release=lambda *_: app.show_vocab()))
        body.add_widget(Button(text="Kalender", on_release=lambda *_: app.show_calendar()))
        layout.add_widget(body)
        self.add_widget(layout)


class TrainingSetupScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(TopBar(app, "Training"))
        body = BoxLayout(orientation="vertical", padding=16, spacing=12)
        body.add_widget(Label(text="Modus"))
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        btn_row.add_widget(Button(text="Einführen", on_release=lambda *_: self._start("introduce")))
        btn_row.add_widget(Button(text="Wiederholen", on_release=lambda *_: self._start("review")))
        body.add_widget(btn_row)
        body.add_widget(Label(text="Richtung"))
        dir_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        dir_row.add_widget(Button(text="DE → EN", on_release=lambda *_: self._set_dir("de_to_en")))
        dir_row.add_widget(Button(text="EN → DE", on_release=lambda *_: self._set_dir("en_to_de")))
        body.add_widget(dir_row)
        self.dir_label = Label(text="Aktuell: DE → EN")
        body.add_widget(self.dir_label)
        layout.add_widget(body)
        self.add_widget(layout)
        self._direction = "de_to_en"

    def _set_dir(self, direction: str) -> None:
        self._direction = direction
        self.dir_label.text = "Aktuell: " + ("DE → EN" if direction == "de_to_en" else "EN → DE")

    def _start(self, mode: str) -> None:
        self.app.start_training(mode, self._direction)


class TrainingScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(TopBar(app, "Training"))
        body = BoxLayout(orientation="vertical", padding=16, spacing=10)
        self.timer_label = Label(text="05:00")
        body.add_widget(self.timer_label)
        self.prompt_label = Label(text="")
        body.add_widget(self.prompt_label)
        self.answer_input = TextInput(multiline=False, size_hint_y=None, height=44)
        body.add_widget(self.answer_input)
        self.feedback_label = Label(text="")
        body.add_widget(self.feedback_label)
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        btn_row.add_widget(Button(text="OK", on_release=lambda *_: self.submit()))
        btn_row.add_widget(Button(text="Abbrechen", on_release=lambda *_: self.app.end_training(cancelled=True)))
        body.add_widget(btn_row)
        layout.add_widget(body)
        self.add_widget(layout)

    def on_pre_enter(self, *args):
        self.answer_input.text = ""
        self.feedback_label.text = ""
        self.app.update_training_view()

    def submit(self) -> None:
        self.app.submit_answer(self.answer_input.text)


class VocabScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(TopBar(app, "Vokabeln"))
        body = BoxLayout(orientation="vertical", padding=16, spacing=8)

        body.add_widget(Label(text="Sprache"))
        self.lang_spinner = Spinner(text="", values=[], size_hint_y=None, height=40)
        self.lang_spinner.bind(text=lambda *_: self._refresh_topics())
        body.add_widget(self.lang_spinner)

        body.add_widget(Label(text="Thema"))
        self.topic_spinner = Spinner(text="", values=[], size_hint_y=None, height=40)
        self.topic_spinner.bind(text=lambda *_: self._refresh_cards())
        body.add_widget(self.topic_spinner)

        body.add_widget(Label(text="Neues Thema (optional)"))
        self.topic_input = TextInput(multiline=False, size_hint_y=None, height=40)
        body.add_widget(self.topic_input)

        self.cards_label = Label(text="Vorhandene Vokabeln", size_hint_y=None, height=24)
        body.add_widget(self.cards_label)
        self.cards_layout = BoxLayout(orientation="vertical", spacing=4, size_hint_y=None)
        self.cards_layout.bind(minimum_height=self.cards_layout.setter("height"))
        cards_scroll = ScrollView(size_hint=(1, None), height=120)
        cards_scroll.add_widget(self.cards_layout)
        body.add_widget(cards_scroll)

        body.add_widget(Label(text="Deutsch"))
        self.de_input = TextInput(multiline=False, size_hint_y=None, height=40)
        body.add_widget(self.de_input)
        body.add_widget(Label(text="Zielsprache"))
        self.en_input = TextInput(multiline=False, size_hint_y=None, height=40)
        body.add_widget(self.en_input)
        body.add_widget(Label(text="Eselsbrücke DE → EN"))
        self.hint_de_input = TextInput(multiline=False, size_hint_y=None, height=40)
        body.add_widget(self.hint_de_input)
        body.add_widget(Label(text="Eselsbrücke EN → DE"))
        self.hint_en_input = TextInput(multiline=False, size_hint_y=None, height=40)
        body.add_widget(self.hint_en_input)
        body.add_widget(Button(text="Speichern", size_hint_y=None, height=44, on_release=lambda *_: self._save()))
        layout.add_widget(body)
        self.add_widget(layout)

    def on_pre_enter(self, *args):
        self._refresh_languages()

    def _refresh_languages(self) -> None:
        langs = self.app.get_target_languages()
        self.lang_spinner.values = langs
        if langs:
            self.lang_spinner.text = langs[0]
        self._refresh_topics()

    def _refresh_topics(self) -> None:
        lang = self.lang_spinner.text
        topics = self.app.get_topics(lang)
        self.topic_spinner.values = topics
        self.topic_spinner.text = topics[0] if topics else ""
        self._refresh_cards()

    def _refresh_cards(self) -> None:
        self.cards_layout.clear_widgets()
        lang = self.lang_spinner.text
        topic_name = self.topic_spinner.text
        for card in self.app.get_cards_for_topic(lang, topic_name):
            self.cards_layout.add_widget(Label(text=f"{card['de']} — {card['en']}", size_hint_y=None, height=22))

    def _save(self) -> None:
        lang = self.lang_spinner.text
        topic = self.topic_input.text.strip() or self.topic_spinner.text.strip()
        de = self.de_input.text.strip()
        en = self.en_input.text.strip()
        hint_de = self.hint_de_input.text.strip()
        hint_en = self.hint_en_input.text.strip()
        self.app.add_vocab(lang, topic, de, en, hint_de, hint_en)
        self.topic_input.text = ""
        self.de_input.text = ""
        self.en_input.text = ""
        self.hint_de_input.text = ""
        self.hint_en_input.text = ""
        self._refresh_topics()


class CalendarScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(TopBar(app, "Kalender"))
        self.body = BoxLayout(orientation="vertical", padding=16, spacing=8)
        self.month_label = Label(text="")
        self.body.add_widget(self.month_label)
        self.grid = GridLayout(cols=7, spacing=4, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.grid)
        self.body.add_widget(scroll)
        layout.add_widget(self.body)
        self.add_widget(layout)

    def on_pre_enter(self, *args):
        self._build_month()

    def _build_month(self):
        self.grid.clear_widgets()
        now = datetime.now()
        self.month_label.text = now.strftime("%B %Y")
        counts = self.app.training_counts_by_day()

        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for wd in weekdays:
            self.grid.add_widget(Label(text=wd, bold=True))

        cal = calendar.Calendar(firstweekday=0)
        for day in cal.itermonthdates(now.year, now.month):
            if day.month != now.month:
                self.grid.add_widget(Label(text=""))
                continue
            key = day.isoformat()
            count = counts.get(key, 0)
            marker = "★" if count > 0 else ""
            label = f"{day.day}\n{marker}{count if count > 0 else ''}"
            self.grid.add_widget(Label(text=label))


class JonMemApp(App):
    def build(self):
        self.title = "JonMem"
        self._error_log = []
        self._last_exception = ""

        self.data_dir = self.user_data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.vocab_path = os.path.join(self.data_dir, "vocab.yaml")
        self.progress_path = os.path.join(self.data_dir, "progress.json")
        self.log_path = os.path.join(self.data_dir, "training_log.json")
        self.beep_path = os.path.join(self.data_dir, "success.wav")
        self.backup_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

        self._ensure_seed_vocab()
        self.vocab = self._load_vocab()
        self.progress = _load_json(self.progress_path, {})
        self.training_log = _load_json(self.log_path, [])

        try:
            _ensure_beep(self.beep_path)
            self._sound_success = SoundLoader.load(self.beep_path)
        except Exception:
            self._sound_success = None

        self._check_notification()

        self.session_items = []
        self.session_index = 0
        self.session_correct = 0
        self.session_start = None
        self.session_mode = None
        self.session_direction = "de_to_en"
        self.time_left = SESSION_SECONDS
        self._timer_event = None

        self.sm = ScreenManager()
        self.screen_menu = MenuScreen(self, name="menu")
        self.screen_setup = TrainingSetupScreen(self, name="setup")
        self.screen_train = TrainingScreen(self, name="train")
        self.screen_vocab = VocabScreen(self, name="vocab")
        self.screen_calendar = CalendarScreen(self, name="calendar")
        self.sm.add_widget(self.screen_menu)
        self.sm.add_widget(self.screen_setup)
        self.sm.add_widget(self.screen_train)
        self.sm.add_widget(self.screen_vocab)
        self.sm.add_widget(self.screen_calendar)
        self.sm.current = "menu"
        return self.sm

    def _log_error(self, label: str, exc: Exception | None = None) -> None:
        msg = f"[{datetime.now().isoformat(timespec='seconds')}] {label}"
        if exc is not None:
            msg += f": {exc}"
        self._error_log.append(msg)
        if exc is not None:
            self._last_exception = traceback.format_exc()

    def _ensure_seed_vocab(self) -> None:
        if os.path.exists(self.vocab_path):
            return
        try:
            os.makedirs(os.path.dirname(self.vocab_path), exist_ok=True)
            with open(SEED_VOCAB_PATH, "rb") as src, open(self.vocab_path, "wb") as dst:
                dst.write(src.read())
        except Exception as exc:
            self._log_error("seed copy failed", exc)

    def _load_vocab(self) -> dict:
        try:
            return _load_yaml(self.vocab_path)
        except Exception as exc:
            self._log_error("vocab load failed", exc)
            return {"meta": {}, "topics": [], "cards": []}

    def _save_vocab(self) -> None:
        try:
            _save_yaml(self.vocab_path, self.vocab)
        except Exception as exc:
            self._log_error("vocab save failed", exc)

    def get_target_languages(self):
        meta = self.vocab.get("meta", {})
        langs = meta.get("target_langs") or []
        if isinstance(langs, str):
            langs = [langs]
        if not langs:
            langs = ["en"]
        return langs

    def get_topics(self, lang: str):
        topics = []
        for topic in self.vocab.get("topics", []):
            if topic.get("lang", "en") == lang:
                topics.append(topic.get("name", ""))
        return [t for t in topics if t]

    def get_cards_for_topic(self, lang: str, topic_name: str):
        topic_id = None
        for topic in self.vocab.get("topics", []):
            if topic.get("name") == topic_name and topic.get("lang", "en") == lang:
                topic_id = topic.get("id")
                break
        if not topic_id:
            return []
        cards = []
        for card in self.vocab.get("cards", []):
            if card.get("topic") == topic_id and card.get("lang", "en") == lang:
                cards.append(card)
        return cards

    def show_training_setup(self) -> None:
        self.sm.current = "setup"

    def show_vocab(self) -> None:
        self.sm.current = "vocab"

    def show_calendar(self) -> None:
        self.sm.current = "calendar"

    def open_menu(self, *_):
        layout = BoxLayout(orientation="vertical", spacing=6, padding=10)
        layout.add_widget(Button(text="Lizenz", size_hint_y=None, height=40, on_release=lambda *_: self._show_license()))
        layout.add_widget(Button(text="Unterstütze mich", size_hint_y=None, height=40, on_release=lambda *_: self._open_support()))
        layout.add_widget(Button(text="Backup exportieren", size_hint_y=None, height=40, on_release=lambda *_: self._export_backup()))
        layout.add_widget(Button(text="Backup importieren", size_hint_y=None, height=40, on_release=lambda *_: self._import_backup_prompt()))
        layout.add_widget(Button(text="Debug report", size_hint_y=None, height=40, on_release=lambda *_: self._show_debug_report()))
        layout.add_widget(Button(text="Schließen", size_hint_y=None, height=40, on_release=lambda *_: popup.dismiss()))
        popup = Popup(title="Menü", content=layout, size_hint=(0.8, 0.7))
        popup.open()

    def _show_license(self) -> None:
        try:
            text = _read_text(os.path.join(os.path.dirname(__file__), "License.txt"))
        except Exception as exc:
            text = f"License not available: {exc}"
        content = TextInput(text=text, readonly=True)
        Popup(title="Lizenz", content=content, size_hint=(0.9, 0.9)).open()

    def _open_support(self) -> None:
        import webbrowser
        webbrowser.open(SUPPORT_URL)

    def _export_backup(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.backup_dir, f"backup_{timestamp}.yaml")
        payload = {
            "meta": {"created": datetime.now().isoformat(timespec="seconds")},
            "vocab": self.vocab,
            "progress": self.progress,
            "training_log": self.training_log,
        }
        try:
            _save_yaml(path, payload)
            Popup(title="Backup", content=Label(text=f"Gespeichert:\n{path}"), size_hint=(0.9, 0.4)).open()
        except Exception as exc:
            self._log_error("backup export failed", exc)
            Popup(title="Backup", content=Label(text=f"Fehler: {exc}"), size_hint=(0.9, 0.4)).open()

    def _import_backup_prompt(self) -> None:
        box = BoxLayout(orientation="vertical", spacing=6, padding=8)
        box.add_widget(Label(text="Pfad zur YAML-Backup-Datei"))
        path_input = TextInput(multiline=False, text="")
        box.add_widget(path_input)

        def do_import(_):
            popup.dismiss()
            self._import_backup(path_input.text.strip())

        box.add_widget(Button(text="Importieren", size_hint_y=None, height=40, on_release=do_import))
        popup = Popup(title="Backup importieren", content=box, size_hint=(0.9, 0.5))
        popup.open()

    def _import_backup(self, path: str) -> None:
        try:
            data = _load_yaml(path)
            if "vocab" in data:
                self.vocab = data["vocab"]
                self._save_vocab()
            if "progress" in data:
                self.progress = data["progress"]
                _save_json(self.progress_path, self.progress)
            if "training_log" in data:
                self.training_log = data["training_log"]
                _save_json(self.log_path, self.training_log)
            Popup(title="Backup", content=Label(text="Import erfolgreich."), size_hint=(0.6, 0.4)).open()
        except Exception as exc:
            self._log_error("backup import failed", exc)
            Popup(title="Backup", content=Label(text=f"Import-Fehler: {exc}"), size_hint=(0.8, 0.4)).open()

    def _show_debug_report(self) -> None:
        lines = ["JonMem Debug Report", f"Version: {__version__}", f"Platform: {kivy_platform}"]
        if self._error_log:
            lines.append("Errors:")
            lines.extend(self._error_log)
        if self._last_exception:
            lines.append("\nLast exception:\n" + self._last_exception)
        content = TextInput(text="\n".join(lines), readonly=True)
        Popup(title="Debug report", content=content, size_hint=(0.95, 0.95)).open()

    def _check_notification(self) -> None:
        if notification is None:
            return
        try:
            last = self._last_training_time()
            if last is None:
                return
            if datetime.now() - last > timedelta(hours=24):
                notification.notify(
                    title="JonMem",
                    message="Dein letztes Training liegt über 24 Stunden zurück.",
                    timeout=5,
                )
        except Exception as exc:
            self._log_error("notification failed", exc)

    def _last_training_time(self):
        if not self.training_log:
            return None
        try:
            last = self.training_log[-1]
            return datetime.fromisoformat(last.get("started"))
        except Exception:
            return None

    def add_vocab(self, lang: str, topic: str, de: str, en: str, hint_de: str, hint_en: str) -> None:
        if not lang:
            Popup(title="Vokabeln", content=Label(text="Bitte zuerst eine Sprache wählen."), size_hint=(0.6, 0.3)).open()
            return
        if not de or not en:
            Popup(title="Vokabeln", content=Label(text="Deutsch und Englisch müssen gesetzt sein."), size_hint=(0.6, 0.3)).open()
            return
        topic = topic.strip() or "Allgemein"
        topic_id = _slugify(topic)
        topics = self.vocab.get("topics", [])
        if not any(t.get("id") == topic_id and t.get("lang", "en") == lang for t in topics):
            topics.append({"id": topic_id, "name": topic, "lang": lang})
        cards = self.vocab.get("cards", [])
        idx = sum(1 for c in cards if c.get("topic") == topic_id and c.get("lang", "en") == lang) + 1
        card_id = f"{topic_id}_{idx:03d}_{lang}"
        cards.append({
            "id": card_id,
            "topic": topic_id,
            "lang": lang,
            "de": de,
            "en": en,
            "hint_de_to_en": hint_de,
            "hint_en_to_de": hint_en,
        })
        self.vocab["topics"] = topics
        self.vocab["cards"] = cards
        meta = self.vocab.setdefault("meta", {})
        target_langs = meta.get("target_langs") or []
        if lang not in target_langs:
            target_langs.append(lang)
        meta["target_langs"] = target_langs
        self._save_vocab()
        Popup(title="Vokabeln", content=Label(text="Gespeichert."), size_hint=(0.4, 0.3)).open()

    def start_training(self, mode: str, direction: str) -> None:
        self.session_mode = mode
        self.session_direction = direction
        self.session_items = self._build_session_items(mode, direction)
        if not self.session_items:
            Popup(title="Training", content=Label(text="Keine passenden Karten gefunden."), size_hint=(0.6, 0.3)).open()
            return
        self.session_index = 0
        self.session_correct = 0
        self.time_left = SESSION_SECONDS
        self.session_start = datetime.now()
        self.sm.current = "train"
        self._start_timer()

    def _build_session_items(self, mode: str, direction: str):
        items = []
        cards = self.vocab.get("cards", [])
        for card in cards:
            card_id = card.get("id")
            if not card_id:
                continue
            prog = self.progress.get(card_id, {}).get(direction)
            if mode == "introduce" and prog is not None:
                continue
            if mode == "review" and prog is None:
                continue
            prompt = card.get("de") if direction == "de_to_en" else card.get("en")
            answer = card.get("en") if direction == "de_to_en" else card.get("de")
            hint = card.get("hint_de_to_en") if direction == "de_to_en" else card.get("hint_en_to_de")
            items.append({
                "id": card_id,
                "prompt": prompt,
                "answer": answer,
                "hint": hint,
                "de": card.get("de", ""),
                "en": card.get("en", ""),
                "hint_de_to_en": card.get("hint_de_to_en", ""),
                "hint_en_to_de": card.get("hint_en_to_de", ""),
            })
        random.shuffle(items)
        return items[:SESSION_MAX_ITEMS]

    def _start_timer(self) -> None:
        if self._timer_event is not None:
            self._timer_event.cancel()
        self._timer_event = Clock.schedule_interval(self._tick, 1)

    def _tick(self, _dt):
        self.time_left -= 1
        self.update_training_view()
        if self.time_left <= 0:
            self.end_training(cancelled=False)

    def update_training_view(self):
        if self.sm.current != "train":
            return
        mins = max(0, self.time_left) // 60
        secs = max(0, self.time_left) % 60
        self.screen_train.timer_label.text = f"{mins:02d}:{secs:02d}"
        if self.session_index < len(self.session_items):
            item = self.session_items[self.session_index]
            self.screen_train.prompt_label.text = item.get("prompt", "")
        else:
            self.screen_train.prompt_label.text = ""

    def submit_answer(self, text: str) -> None:
        if self.session_index >= len(self.session_items):
            return
        item = self.session_items[self.session_index]
        correct = self._evaluate_answer(text, item.get("answer", ""))
        if correct:
            self.session_correct += 1
            if self._sound_success is not None:
                self._sound_success.play()
            self._update_progress(item["id"], True)
        else:
            self._update_progress(item["id"], False)

        # Pause timer while showing feedback
        if self._timer_event is not None:
            self._timer_event.cancel()
            self._timer_event = None

        self._show_answer_popup(item, correct)
        self.screen_train.answer_input.text = ""

    def _show_answer_popup(self, item: dict, correct: bool) -> None:
        status = "Richtig" if correct else "Falsch"
        color = "00cc66" if correct else "ff4444"
        de_text = item.get("de", "")
        en_text = item.get("en", "")
        hint_de = item.get("hint_de_to_en", "")
        hint_en = item.get("hint_en_to_de", "")

        layout = BoxLayout(orientation="vertical", spacing=6, padding=10)
        layout.add_widget(Label(text=f"[color={color}]{status}[/color]", markup=True, size_hint_y=None, height=28))
        layout.add_widget(Label(text=f"Deutsch: {de_text}"))
        layout.add_widget(Label(text=f"Englisch: {en_text}"))
        if hint_de:
            layout.add_widget(Label(text=f"Eselsbrücke DE → EN: {hint_de}"))
        if hint_en:
            layout.add_widget(Label(text=f"Eselsbrücke EN → DE: {hint_en}"))

        def _next(_):
            popup.dismiss()
            self.session_index += 1
            if self.session_index >= len(self.session_items):
                self.end_training(cancelled=False)
            else:
                self._start_timer()
                self.update_training_view()

        layout.add_widget(Button(text="OK", size_hint_y=None, height=40, on_release=_next))
        popup = Popup(title="Lösung", content=layout, size_hint=(0.9, 0.8))
        popup.open()

    def _evaluate_answer(self, given: str, expected: str) -> bool:
        a = _normalize(given)
        b = _normalize(expected)
        if not a or not b:
            return False
        if a == b:
            return True
        dist = _levenshtein(a, b)
        if len(b) <= 4:
            return dist == 0
        if len(b) <= 7:
            return dist <= 1
        return dist <= 2

    def _update_progress(self, card_id: str, correct: bool) -> None:
        entry = self.progress.setdefault(card_id, {})
        dir_entry = entry.setdefault(self.session_direction, {"stage": 1})
        stage = int(dir_entry.get("stage", 1))
        if correct:
            stage = min(MAX_STAGE, stage + 1)
        else:
            stage = max(1, stage - 1)
        dir_entry["stage"] = stage
        dir_entry["last_seen"] = datetime.now().isoformat(timespec="seconds")
        dir_entry["last_result"] = bool(correct)
        _save_json(self.progress_path, self.progress)

    def end_training(self, cancelled: bool) -> None:
        if self._timer_event is not None:
            self._timer_event.cancel()
            self._timer_event = None
        if cancelled:
            self.sm.current = "menu"
            return
        total = len(self.session_items)
        summary = f"{self.session_correct} von {total} richtig."
        self._append_training_log(total)
        Popup(title="Training", content=Label(text=summary), size_hint=(0.6, 0.4)).open()
        self.sm.current = "menu"

    def _append_training_log(self, total: int) -> None:
        entry = {
            "started": (self.session_start or datetime.now()).isoformat(timespec="seconds"),
            "items": total,
            "correct": self.session_correct,
            "mode": self.session_mode,
            "direction": self.session_direction,
        }
        self.training_log.append(entry)
        _save_json(self.log_path, self.training_log)

    def training_counts_by_day(self):
        counts = {}
        for entry in self.training_log:
            try:
                day = entry.get("started", "")[:10]
            except Exception:
                continue
            if day:
                counts[day] = counts.get(day, 0) + 1
        return counts


if __name__ == "__main__":
    JonMemApp().run()
