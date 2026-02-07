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
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.utils import platform as kivy_platform, escape_markup
import training

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
IS_IOS = (kivy_platform == "ios")

SEED_VOCAB_PATH = os.path.join(os.path.dirname(__file__), "data", "seed_vocab.yaml")

SESSION_MAX_ITEMS = 10
SESSION_SECONDS = 300
MAX_STAGE = 4
INTRODUCE_REPEAT_COUNT = 2
PYRAMID_STAGE_WEIGHTS = {
    1: 4,
    2: 3,
    3: 2,
    4: 1,
}

MENU_ICON = "\u2261"
STAR_ICON = "\u2605"
MOON_ICON = "\u263E"
FONT_PATH = os.path.join(os.path.dirname(__file__), "data", "fonts", "DejaVuSans.ttf")
APP_FONT_NAME = None

SUPPORT_URL = "https://www.paypal.com/donate/?hosted_button_id=PND6Y8CGNZVW6"

BASE_INPUT_HEIGHT = 72
BASE_BUTTON_HEIGHT = 64
BASE_INPUT_FONT_SIZE = 26
BASE_BUTTON_FONT_SIZE = 26
BASE_SPINNER_FONT_SIZE = 26
BASE_LABEL_FONT_SIZE = 24
TEXT_COLOR = (0.12, 0.1, 0.08, 1)
SURFACE_BG = (0.98, 0.96, 0.93, 1)
CARD_BG = (0.94, 0.92, 0.88, 1)
CARD_BORDER = (0.72, 0.68, 0.63, 1)
LEVEL_BG_2 = (0.88, 0.96, 0.9, 1)
LEVEL_BG_3 = (0.88, 0.93, 0.99, 1)
LEVEL_BG_4 = (0.96, 0.88, 0.95, 1)
INPUT_BG = (1, 1, 1, 1)
BUTTON_BG = (0.86, 0.83, 0.78, 1)
BASE_CARD_HEIGHT = 68
BASE_CALENDAR_CELL_HEIGHT = 70

try:
    from plyer import filechooser  # type: ignore
except Exception:
    filechooser = None


def _ui_scale() -> float:
    short_edge = min(Window.width or 0, Window.height or 0)
    if short_edge <= 0:
        return 1.0
    scale = short_edge / 720.0
    return max(0.85, min(1.6, scale))


def _ui(value: float) -> float:
    return max(1.0, value * _ui_scale())


def _scroll_to_widget(widget) -> None:
    parent = widget.parent
    while parent is not None:
        if isinstance(parent, ScrollView):
            parent.scroll_to(widget, padding=_ui(12))
            break
        parent = parent.parent


class SmartTextInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        if substring in ("\b", "\x08", "\x7f"):
            self.do_backspace(from_undo=from_undo)
            return
        return super().insert_text(substring, from_undo=from_undo)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if hasattr(self, "halign"):
            self.halign = "center"


class ReadableSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = CARD_BG
        self.color = TEXT_COLOR
        self.font_size = _ui(BASE_SPINNER_FONT_SIZE)
        self.height = _ui(BASE_INPUT_HEIGHT)
        if APP_FONT_NAME:
            self.font_name = APP_FONT_NAME


def _styled_text_input(**kwargs) -> TextInput:
    kwargs.setdefault("font_size", _ui(BASE_INPUT_FONT_SIZE))
    kwargs.setdefault("foreground_color", TEXT_COLOR)
    kwargs.setdefault("background_color", INPUT_BG)
    if APP_FONT_NAME:
        kwargs.setdefault("font_name", APP_FONT_NAME)
    return SmartTextInput(**kwargs)


def _styled_spinner(**kwargs) -> Spinner:
    kwargs.setdefault("font_size", _ui(BASE_SPINNER_FONT_SIZE))
    kwargs.setdefault("option_cls", ReadableSpinnerOption)
    if APP_FONT_NAME:
        kwargs.setdefault("font_name", APP_FONT_NAME)
    return Spinner(**kwargs)

def _styled_label(text: str, **kwargs) -> Label:
    kwargs.setdefault("font_size", _ui(BASE_LABEL_FONT_SIZE))
    kwargs.setdefault("color", TEXT_COLOR)
    if APP_FONT_NAME:
        kwargs.setdefault("font_name", APP_FONT_NAME)
    label = Label(text=text, **kwargs)
    label.size_hint_y = None
    label.bind(size=lambda lbl, *_: setattr(lbl, "text_size", (lbl.width, None)))
    label.bind(texture_size=lambda lbl, size: setattr(lbl, "height", size[1] + _ui(6)))
    return label


def _make_scrollable(container: BoxLayout) -> ScrollView:
    container.size_hint_y = None
    container.bind(minimum_height=container.setter("height"))
    scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
    scroll.add_widget(container)
    return scroll


def _styled_popup(**kwargs) -> Popup:
    kwargs.setdefault("background", "")
    kwargs.setdefault("background_color", SURFACE_BG)
    kwargs.setdefault("separator_color", CARD_BORDER)
    return Popup(**kwargs)

def _level_bg_color(level: int) -> tuple[float, float, float, float]:
    if level == 2:
        return LEVEL_BG_2
    if level == 3:
        return LEVEL_BG_3
    if level >= 4:
        return LEVEL_BG_4
    return CARD_BG


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


def _dump_yaml_bytes(data: dict) -> bytes:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    return text.encode("utf-8")


def _load_yaml_bytes(raw: bytes) -> dict:
    if yaml is None:
        raise RuntimeError("pyyaml not available")
    data = yaml.safe_load(raw.decode("utf-8", errors="replace")) or {}
    if not isinstance(data, dict):
        raise ValueError("invalid yaml structure")
    return data


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


def _is_content_uri(path: str) -> bool:
    return isinstance(path, str) and path.startswith("content://")


def _normalize_path(path: str) -> str:
    if isinstance(path, str) and path.startswith("file://"):
        return path[7:]
    return path


def _ensure_yaml_extension(path: str) -> str:
    if _is_content_uri(path):
        return path
    if path.lower().endswith((".yaml", ".yml")):
        return path
    return f"{path}.yaml"


def _tk_save_file(title: str, initial_dir: str, default_name: str) -> str | None:
    try:
        import tkinter  # type: ignore
        from tkinter import filedialog  # type: ignore
    except Exception:
        return None
    root = tkinter.Tk()
    root.withdraw()
    try:
        path = filedialog.asksaveasfilename(
            title=title,
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".yaml",
            filetypes=[("YAML", "*.yaml"), ("All files", "*.*")],
        )
    finally:
        root.destroy()
    return path or None


def _android_read_uri(uri: str) -> bytes:
    if not IS_ANDROID:
        raise RuntimeError("android uri read not available")
    from jnius import autoclass, jarray  # type: ignore
    Uri = autoclass("android.net.Uri")
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    resolver = activity.getContentResolver()
    juri = Uri.parse(uri)
    stream = resolver.openInputStream(juri)
    if stream is None:
        raise RuntimeError("unable to open input stream")
    ByteArrayOutputStream = autoclass("java.io.ByteArrayOutputStream")
    buffer = jarray("b")(4096)
    baos = ByteArrayOutputStream()
    try:
        while True:
            count = stream.read(buffer)
            if count == -1:
                break
            baos.write(buffer, 0, count)
    finally:
        stream.close()
    data = baos.toByteArray()
    return bytes(data)


def _android_write_uri(uri: str, data: bytes) -> None:
    if not IS_ANDROID:
        raise RuntimeError("android uri write not available")
    from jnius import autoclass, jarray  # type: ignore
    Uri = autoclass("android.net.Uri")
    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    resolver = activity.getContentResolver()
    juri = Uri.parse(uri)
    stream = resolver.openOutputStream(juri)
    if stream is None:
        raise RuntimeError("unable to open output stream")
    try:
        stream.write(jarray("b")(data))
        stream.flush()
    finally:
        stream.close()


def _ensure_beep(path: str, *, freq: float = 880.0, duration: float = 0.12) -> None:
    if os.path.exists(path):
        return
    framerate = 44100
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
        super().__init__(orientation="horizontal", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), **kwargs)
        self.app = app
        button_kwargs = {
            "text": MENU_ICON,
            "size_hint_x": None,
            "width": _ui(BASE_BUTTON_HEIGHT),
            "on_release": self.app.open_menu,
        }
        if APP_FONT_NAME:
            button_kwargs["font_name"] = APP_FONT_NAME
        self.add_widget(Button(**button_kwargs))
        self.add_widget(Label(text=title, font_size=_ui(BASE_LABEL_FONT_SIZE + 4), color=TEXT_COLOR))


class CardRow(BoxLayout):
    def __init__(self, text: str, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=_ui(BASE_CARD_HEIGHT), padding=10, **kwargs)
        with self.canvas.before:
            Color(*CARD_BG)
            self._bg = RoundedRectangle(radius=[10], pos=self.pos, size=self.size)
            Color(*CARD_BORDER)
            self._border = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 10])
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        label = Label(text=text, halign="left", valign="middle",
                      font_size=_ui(BASE_LABEL_FONT_SIZE), color=TEXT_COLOR)
        label.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))
        self.add_widget(label)

    def _update_canvas(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = [self.x, self.y, self.width, self.height, 10]


class VocabRow(BoxLayout):
    def __init__(self, card: dict, on_edit, on_delete, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=_ui(BASE_CARD_HEIGHT),
                         padding=6, spacing=6, **kwargs)
        label = Label(text=f"{card.get('de', '')} — {card.get('en', '')}",
                      halign="left", valign="middle", font_size=_ui(BASE_LABEL_FONT_SIZE), color=TEXT_COLOR)
        label.bind(size=lambda lbl, *_: setattr(lbl, "text_size", lbl.size))
        self.add_widget(label)
        self.add_widget(Button(text="Bearbeiten", size_hint_x=None, width=_ui(160),
                               on_release=lambda *_: on_edit(card)))
        self.add_widget(Button(text="Löschen", size_hint_x=None, width=_ui(130),
                               on_release=lambda *_: on_delete(card)))


class CalendarCell(BoxLayout):
    def __init__(self, day_text: str, count_text: str, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=_ui(BASE_CALENDAR_CELL_HEIGHT), padding=4, **kwargs)
        day_kwargs = {"text": day_text, "size_hint_y": None, "height": _ui(24)}
        count_kwargs = {"text": count_text}
        if APP_FONT_NAME:
            day_kwargs["font_name"] = APP_FONT_NAME
            count_kwargs["font_name"] = APP_FONT_NAME
        self.add_widget(Label(**day_kwargs))
        self.add_widget(Label(**count_kwargs))


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
        body = BoxLayout(orientation="vertical", padding=_ui(16), spacing=_ui(12))
        body.add_widget(_styled_label("Modus"))
        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="Einführen", on_release=lambda *_: self._start("introduce")))
        btn_row.add_widget(Button(text="Wiederholen", on_release=lambda *_: self._start("review")))
        body.add_widget(btn_row)
        body.add_widget(_styled_label("Sprache"))
        self.lang_spinner = _styled_spinner(text="", values=[], size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT))
        self.lang_spinner.bind(text=lambda _spinner, text: self._set_lang(text))
        body.add_widget(self.lang_spinner)
        self.lang_label = _styled_label("")
        body.add_widget(self.lang_label)
        body.add_widget(_styled_label("Unfertige Kategorien (Einführen)"))
        self.intro_status = _styled_label("")
        body.add_widget(self.intro_status)
        body.add_widget(_styled_label("Richtung"))
        dir_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        self.dir_de = ToggleButton(text="DE → EN", group="direction", state="down")
        self.dir_en = ToggleButton(text="EN → DE", group="direction")
        self.dir_de.bind(state=lambda btn, state: self._toggle_dir(btn, state, "de_to_en"))
        self.dir_en.bind(state=lambda btn, state: self._toggle_dir(btn, state, "en_to_de"))
        dir_row.add_widget(self.dir_de)
        dir_row.add_widget(self.dir_en)
        body.add_widget(dir_row)
        self.dir_label = _styled_label("Aktuell: DE → EN")
        body.add_widget(self.dir_label)
        body.add_widget(_styled_label("Themen (nur Wiederholen)"))
        self.topic_status = _styled_label("")
        body.add_widget(self.topic_status)
        body.add_widget(Button(text="Themen wählen (Experten)", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                               on_release=lambda *_: self._open_topic_picker()))
        body.add_widget(Button(text="Zurück", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                               on_release=lambda *_: self.app.show_menu()))
        layout.add_widget(body)
        self.add_widget(layout)
        self._direction = "de_to_en"
        self._lang = ""

    def _toggle_dir(self, _btn, state: str, direction: str) -> None:
        if state == "down":
            self._set_dir(direction)

    def _set_dir(self, direction: str) -> None:
        self._direction = direction
        self._update_direction_labels()
        self._refresh_intro_status()

    def _start(self, mode: str) -> None:
        lang = self._lang or (self.lang_spinner.text or "").strip()
        self.app.start_training(mode, self._direction, lang, self._topic_filter(), self._topic_filter_enabled())

    def on_pre_enter(self, *args):
        self._refresh_languages()
        self._refresh_intro_status()
        self._refresh_topic_status()

    def _refresh_languages(self) -> None:
        langs = self.app.get_target_languages()
        self.lang_spinner.values = langs
        if self._lang and self._lang in langs:
            self.lang_spinner.text = self._lang
        elif langs:
            self.lang_spinner.text = langs[0]
            self._set_lang(langs[0])
        else:
            self.lang_spinner.text = ""
            self._set_lang("")

    def _set_lang(self, lang: str) -> None:
        self._lang = (lang or "").strip()
        if self._lang:
            self.lang_label.text = f"Aktuell: {self._lang}"
        else:
            self.lang_label.text = "Aktuell: -"
        self._update_direction_labels()
        self._refresh_intro_status()
        self._refresh_topic_status()

    def _update_direction_labels(self) -> None:
        lang = (self._lang or "en").upper()
        self.dir_de.text = f"DE → {lang}"
        self.dir_en.text = f"{lang} → DE"
        current = "DE → {lang}" if self._direction == "de_to_en" else "{lang} → DE"
        self.dir_label.text = "Aktuell: " + current.format(lang=lang)

    def _topic_filter_enabled(self) -> bool:
        return self.app.is_review_topic_filter_enabled(self._lang)

    def _topic_filter(self) -> list[str]:
        return self.app.get_review_topic_filter(self._lang)

    def _refresh_topic_status(self) -> None:
        if not self._lang:
            self.topic_status.text = "Themen: -"
            return
        if not self._topic_filter_enabled():
            self.topic_status.text = "Themen: Alle (Standard)"
            return
        selected = self._topic_filter()
        self.topic_status.text = f"Themen: {len(selected)} gewählt"

    def _refresh_intro_status(self) -> None:
        if not self._lang:
            self.intro_status.text = "Kategorien: -"
            return
        items = self.app.get_intro_topic_progress(self._lang, self._direction)
        if not items:
            self.intro_status.text = "Kategorien: Alle abgeschlossen"
            return
        lines = [f"{it['name']}: {it['percent']}%" for it in items]
        self.intro_status.text = "Kategorien:\n" + "\n".join(lines)

    def _open_topic_picker(self) -> None:
        lang = self._lang or (self.lang_spinner.text or "").strip()
        if not lang:
            _styled_popup(title="Themen", content=Label(text="Bitte zuerst eine Sprache wählen."),
                          size_hint=(0.7, 0.3)).open()
            return
        topics = self.app.get_learned_topics(lang)
        if not topics:
            _styled_popup(title="Themen", content=Label(text="Noch keine eingeführten Themen vorhanden."),
                          size_hint=(0.8, 0.3)).open()
            return
        if self.app.is_review_topic_filter_enabled(lang):
            selected = set(self.app.get_review_topic_filter(lang))
        else:
            selected = {topic["id"] for topic in topics}

        box = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(8))
        box.add_widget(_styled_label(f"Sprache: {lang}"))
        box.add_widget(_styled_label("Themen auswählen"))
        list_box = BoxLayout(orientation="vertical", spacing=_ui(6), size_hint_y=None)
        list_box.bind(minimum_height=list_box.setter("height"))
        toggles = []
        for topic in topics:
            state = "down" if topic["id"] in selected else "normal"
            toggle = ToggleButton(text=topic["name"], state=state, size_hint_y=None,
                                  height=_ui(BASE_BUTTON_HEIGHT))
            list_box.add_widget(toggle)
            toggles.append((topic["id"], toggle))
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(list_box)
        box.add_widget(scroll)

        def do_save(_):
            chosen = [topic_id for topic_id, toggle in toggles if toggle.state == "down"]
            if not chosen:
                _styled_popup(title="Themen", content=Label(text="Bitte mindestens ein Thema wählen."),
                              size_hint=(0.7, 0.3)).open()
                return
            self.app.set_review_topic_filter(lang, chosen, enabled=True)
            popup.dismiss()
            self._refresh_topic_status()

        def do_default(_):
            self.app.set_review_topic_filter(lang, [], enabled=False)
            popup.dismiss()
            self._refresh_topic_status()

        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="Speichern", on_release=do_save))
        btn_row.add_widget(Button(text="Standard (alle)", on_release=do_default))
        btn_row.add_widget(Button(text="Abbrechen", on_release=lambda *_: popup.dismiss()))
        box.add_widget(btn_row)
        popup = _styled_popup(title="Themen", content=_make_scrollable(box), size_hint=(0.9, 0.8))
        popup.open()


class TrainingScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(TopBar(app, "Training"))
        body = BoxLayout(orientation="vertical", padding=_ui(16), spacing=_ui(10))
        self.timer_label = _styled_label("05:00")
        body.add_widget(self.timer_label)
        self.card_box = BoxLayout(orientation="vertical", padding=_ui(12), spacing=_ui(8),
                                  size_hint_y=None)
        self.card_box.bind(minimum_height=self.card_box.setter("height"))
        with self.card_box.canvas.before:
            self._card_color = Color(*CARD_BG)
            self._card_bg = RoundedRectangle(radius=[12], pos=self.card_box.pos, size=self.card_box.size)
        self.card_box.bind(pos=self._update_card_bg, size=self._update_card_bg)

        self.prompt_label = _styled_label("")
        self.card_box.add_widget(self.prompt_label)

        info_row = BoxLayout(orientation="horizontal", spacing=_ui(8), size_hint_y=None)
        self.category_label = _styled_label("Kategorie: -", font_size=_ui(BASE_LABEL_FONT_SIZE - 2), halign="left")
        self.category_label.size_hint_x = 0.7
        self.level_label = _styled_label("Level 1", font_size=_ui(BASE_LABEL_FONT_SIZE - 2), halign="right")
        self.level_label.size_hint_x = 0.3
        info_row.add_widget(self.category_label)
        info_row.add_widget(self.level_label)
        self.card_box.add_widget(info_row)

        self.answer_input = _styled_text_input(multiline=False, size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT))
        self.card_box.add_widget(self.answer_input)
        self.feedback_label = _styled_label("")
        self.card_box.add_widget(self.feedback_label)
        body.add_widget(self.card_box)
        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="OK", on_release=lambda *_: self.submit()))
        btn_row.add_widget(Button(text="Pyramide", on_release=lambda *_: self.app.show_session_pyramid()))
        btn_row.add_widget(Button(text="Abbrechen", on_release=lambda *_: self.app.end_training(cancelled=True)))
        body.add_widget(btn_row)
        layout.add_widget(_make_scrollable(body))
        self.add_widget(layout)

    def _update_card_bg(self, *_):
        self._card_bg.pos = self.card_box.pos
        self._card_bg.size = self.card_box.size

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
        self.selected_lang = ""
        self.selected_topic = ""
        self.selected_topic_id = ""

        layout = BoxLayout(orientation="vertical")
        layout.add_widget(TopBar(app, "Vokabeln"))

        self.wizard = ScreenManager()
        self.step_lang = Screen(name="vocab_lang")
        self.step_topic = Screen(name="vocab_topic")
        self.step_list = Screen(name="vocab_list")
        self._build_step_lang()
        self._build_step_topic()
        self._build_step_list()
        self.wizard.add_widget(self.step_lang)
        self.wizard.add_widget(self.step_topic)
        self.wizard.add_widget(self.step_list)
        layout.add_widget(self.wizard)
        self.add_widget(layout)

    def on_pre_enter(self, *args):
        self._refresh_languages()

    def _build_step_lang(self) -> None:
        body = BoxLayout(orientation="vertical", padding=_ui(16), spacing=_ui(12))
        body.add_widget(_styled_label("1. Zielsprache wählen oder anlegen"))
        self.lang_spinner = _styled_spinner(text="", values=[], size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT))
        body.add_widget(self.lang_spinner)
        body.add_widget(_styled_label("Neue Zielsprache (optional)"))
        self.new_lang_input = _styled_text_input(multiline=False, size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT),
                                                 hint_text="z.B. en, fr")
        body.add_widget(self.new_lang_input)
        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="Weiter", on_release=lambda *_: self._select_language()))
        btn_row.add_widget(Button(text="Zurück", on_release=lambda *_: self.app.show_menu()))
        body.add_widget(btn_row)
        self.step_lang.add_widget(_make_scrollable(body))

    def _build_step_topic(self) -> None:
        body = BoxLayout(orientation="vertical", padding=_ui(16), spacing=_ui(12))
        self.lang_label = _styled_label("")
        body.add_widget(self.lang_label)
        body.add_widget(_styled_label("2. Thema wählen oder anlegen"))
        self.topic_spinner = _styled_spinner(text="", values=[], size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT))
        body.add_widget(self.topic_spinner)
        body.add_widget(_styled_label("Neues Thema (optional)"))
        self.topic_input = _styled_text_input(multiline=False, size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT),
                                              hint_text="z.B. Reisen")
        body.add_widget(self.topic_input)
        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="Weiter", on_release=lambda *_: self._select_topic()))
        btn_row.add_widget(Button(text="Zurück", on_release=lambda *_: self._go_step("vocab_lang")))
        body.add_widget(btn_row)
        self.step_topic.add_widget(_make_scrollable(body))

    def _build_step_list(self) -> None:
        body = BoxLayout(orientation="vertical", padding=_ui(16), spacing=_ui(12))
        self.topic_label = _styled_label("")
        body.add_widget(self.topic_label)
        self.cards_layout = BoxLayout(orientation="vertical", spacing=6, size_hint_y=None)
        self.cards_layout.bind(minimum_height=self.cards_layout.setter("height"))
        cards_scroll = ScrollView(size_hint=(1, 1))
        cards_scroll.add_widget(self.cards_layout)
        body.add_widget(cards_scroll)
        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="Neu", on_release=lambda *_: self._open_card_editor()))
        btn_row.add_widget(Button(text="Zurück", on_release=lambda *_: self._go_step("vocab_topic")))
        btn_row.add_widget(Button(text="Fertig", on_release=lambda *_: self.app.show_menu()))
        body.add_widget(btn_row)
        self.step_list.add_widget(body)

    def _go_step(self, name: str) -> None:
        self.wizard.current = name

    def _refresh_languages(self) -> None:
        langs = self.app.get_target_languages()
        self.lang_spinner.values = langs
        if self.selected_lang and self.selected_lang in langs:
            self.lang_spinner.text = self.selected_lang
        elif langs:
            self.lang_spinner.text = langs[0]
        else:
            self.lang_spinner.text = ""
        self.new_lang_input.text = ""
        self.wizard.current = "vocab_lang"

    def _refresh_topics(self) -> None:
        topics = self.app.get_topics(self.selected_lang)
        self.topic_spinner.values = topics
        if self.selected_topic and self.selected_topic in topics:
            self.topic_spinner.text = self.selected_topic
        elif topics:
            self.topic_spinner.text = topics[0]
        else:
            self.topic_spinner.text = ""

    def _refresh_cards(self) -> None:
        self.cards_layout.clear_widgets()
        for card in self.app.get_cards_for_topic(self.selected_lang, self.selected_topic):
            self.cards_layout.add_widget(VocabRow(card, self._open_card_editor, self._confirm_delete))

    def _select_language(self) -> None:
        new_lang = self.new_lang_input.text.strip()
        lang = new_lang or self.lang_spinner.text.strip()
        if not lang:
            _styled_popup(title="Vokabeln", content=Label(text="Bitte eine Zielsprache wählen oder anlegen."),
                          size_hint=(0.7, 0.3)).open()
            return
        if new_lang:
            self.app.ensure_target_language(lang)
        self.selected_lang = lang
        self.lang_label.text = f"Sprache: {self.selected_lang}"
        self._refresh_topics()
        self._go_step("vocab_topic")

    def _select_topic(self) -> None:
        topic = self.topic_input.text.strip() or self.topic_spinner.text.strip()
        if not topic:
            _styled_popup(title="Vokabeln", content=Label(text="Bitte ein Thema wählen oder anlegen."),
                          size_hint=(0.7, 0.3)).open()
            return
        self.selected_topic_id = self.app.ensure_topic(self.selected_lang, topic)
        self.selected_topic = topic
        self.topic_input.text = ""
        self.topic_label.text = f"3. Vokabeln für {self.selected_lang} / {self.selected_topic}"
        self._refresh_cards()
        self._go_step("vocab_list")

    def _open_card_editor(self, card: dict | None = None) -> None:
        title = "Vokabel bearbeiten" if card else "Neue Vokabel"
        box = BoxLayout(orientation="vertical", spacing=_ui(8), padding=_ui(8))
        box.add_widget(_styled_label("Deutsch"))
        de_input = _styled_text_input(multiline=False, size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT))
        box.add_widget(de_input)
        box.add_widget(_styled_label("Zielsprache"))
        en_input = _styled_text_input(multiline=False, size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT))
        box.add_widget(en_input)
        box.add_widget(_styled_label("Eselsbrücke DE → EN"))
        hint_de_input = _styled_text_input(multiline=False, size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT))
        box.add_widget(hint_de_input)
        box.add_widget(_styled_label("Eselsbrücke EN → DE"))
        hint_en_input = _styled_text_input(multiline=False, size_hint_y=None, height=_ui(BASE_INPUT_HEIGHT))
        box.add_widget(hint_en_input)

        if card:
            de_input.text = card.get("de", "")
            en_input.text = card.get("en", "")
            hint_de_input.text = card.get("hint_de_to_en", "")
            hint_en_input.text = card.get("hint_en_to_de", "")

        def do_save(_):
            de = de_input.text.strip()
            en = en_input.text.strip()
            hint_de = hint_de_input.text.strip()
            hint_en = hint_en_input.text.strip()
            if not de or not en:
                _styled_popup(title="Vokabeln", content=Label(text="Deutsch und Zielsprache müssen gesetzt sein."),
                              size_hint=(0.7, 0.3)).open()
                return
            if card:
                self.app.update_card(card.get("id", ""), de, en, hint_de, hint_en)
                _styled_popup(title="Vokabeln", content=Label(text="Gespeichert."), size_hint=(0.4, 0.3)).open()
            else:
                self.app.add_vocab(self.selected_lang, self.selected_topic, de, en, hint_de, hint_en)
            popup.dismiss()
            self._refresh_cards()

        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="Speichern", on_release=do_save))
        btn_row.add_widget(Button(text="Abbrechen", on_release=lambda *_: popup.dismiss()))
        box.add_widget(btn_row)
        popup = _styled_popup(title=title, content=_make_scrollable(box), size_hint=(0.95, 0.9))
        popup.open()

    def _confirm_delete(self, card: dict) -> None:
        box = BoxLayout(orientation="vertical", spacing=_ui(8), padding=_ui(8))
        box.add_widget(_styled_label("Vokabel löschen?"))

        def do_delete(_):
            self.app.delete_card(card.get("id", ""))
            popup.dismiss()
            self._refresh_cards()

        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="Löschen", on_release=do_delete))
        btn_row.add_widget(Button(text="Abbrechen", on_release=lambda *_: popup.dismiss()))
        box.add_widget(btn_row)
        popup = _styled_popup(title="Vokabeln", content=box, size_hint=(0.7, 0.3))
        popup.open()


class CalendarScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(TopBar(app, "Kalender"))
        self.body = BoxLayout(orientation="vertical", padding=_ui(16), spacing=_ui(8))
        self.month_label = _styled_label("")
        self.body.add_widget(self.month_label)
        self.header_grid = GridLayout(cols=7, spacing=_ui(4), size_hint_y=None, height=_ui(24))
        self.grid = GridLayout(cols=7, spacing=4, size_hint_y=None, row_force_default=True,
                               row_default_height=_ui(BASE_CALENDAR_CELL_HEIGHT))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.body.add_widget(self.header_grid)
        scroll = ScrollView()
        scroll.add_widget(self.grid)
        self.body.add_widget(scroll)
        self.body.add_widget(Button(text="Zurück", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                                    on_release=lambda *_: app.show_menu()))
        layout.add_widget(self.body)
        self.add_widget(layout)

    def on_pre_enter(self, *args):
        self._build_month()

    def _build_month(self):
        self.grid.clear_widgets()
        self.header_grid.clear_widgets()
        now = datetime.now()
        self.month_label.text = now.strftime("%B %Y")
        counts = self.app.training_counts_by_day()

        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for wd in weekdays:
            self.header_grid.add_widget(Label(text=wd, bold=True, font_size=_ui(BASE_LABEL_FONT_SIZE), color=TEXT_COLOR))

        cal = calendar.Calendar(firstweekday=0)
        for day in cal.itermonthdates(now.year, now.month):
            if day.month != now.month:
                self.grid.add_widget(CalendarCell("", ""))
                continue
            key = day.isoformat()
            day_counts = counts.get(key, {"introduce": 0, "review": 0})
            introduce_count = day_counts.get("introduce", 0)
            review_count = day_counts.get("review", 0)
            parts = []
            if introduce_count > 0:
                parts.append(f"{MOON_ICON}{introduce_count}")
            if review_count > 0:
                parts.append(f"{STAR_ICON}{review_count}")
            count_text = " ".join(parts)
            self.grid.add_widget(CalendarCell(str(day.day), count_text))


class JonMemApp(App):
    def build(self):
        global APP_FONT_NAME
        self.title = "JonMem"
        self._error_log = []
        self._last_exception = ""
        if os.path.exists(FONT_PATH):
            LabelBase.register(name="DejaVuSans", fn_regular=FONT_PATH)
            APP_FONT_NAME = "DejaVuSans"
        Button.font_size = _ui(BASE_BUTTON_FONT_SIZE)
        ToggleButton.font_size = _ui(BASE_BUTTON_FONT_SIZE)
        Spinner.font_size = _ui(BASE_SPINNER_FONT_SIZE)
        Label.font_size = _ui(BASE_LABEL_FONT_SIZE)
        Label.color = TEXT_COLOR
        Button.color = TEXT_COLOR
        Button.background_normal = ""
        Button.background_color = BUTTON_BG
        Spinner.color = TEXT_COLOR
        Spinner.background_normal = ""
        Spinner.background_color = BUTTON_BG
        if IS_ANDROID:
            Window.softinput_mode = "resize"
        Window.bind(on_focus=self._on_window_focus)
        Window.clearcolor = SURFACE_BG

        self.data_dir = self.user_data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.vocab_path = os.path.join(self.data_dir, "vocab.yaml")
        self.progress_path = os.path.join(self.data_dir, "progress.json")
        self.log_path = os.path.join(self.data_dir, "training_log.json")
        self.settings_path = os.path.join(self.data_dir, "settings.json")
        self.beep_path = os.path.join(self.data_dir, "success.wav")
        self.almost_beep_path = os.path.join(self.data_dir, "almost.wav")
        self.new_card_beep_path = os.path.join(self.data_dir, "new_card.wav")
        self.backup_dir = os.path.join(self.data_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

        self._ensure_seed_vocab()
        self.vocab = self._load_vocab()
        self.progress = _load_json(self.progress_path, {})
        self.training_log = _load_json(self.log_path, [])
        self.settings = _load_json(self.settings_path, {
            "review_topics_by_lang": {},
            "review_topic_filter_enabled": {},
        })

        try:
            _ensure_beep(self.beep_path, freq=880.0, duration=0.12)
            _ensure_beep(self.almost_beep_path, freq=660.0, duration=0.12)
            _ensure_beep(self.new_card_beep_path, freq=520.0, duration=0.14)
            self._sound_success = SoundLoader.load(self.beep_path)
            self._sound_almost = SoundLoader.load(self.almost_beep_path)
            self._sound_new_card = SoundLoader.load(self.new_card_beep_path)
        except Exception:
            self._sound_success = None
            self._sound_almost = None
            self._sound_new_card = None

        self._check_notification()

        self.session_items = []
        self.session_index = 0
        self.session_correct = 0
        self.session_start = None
        self.session_mode = None
        self.session_direction = "de_to_en"
        langs = self.get_target_languages()
        self.session_lang = langs[0] if langs else "en"
        self.session_topic_filter_enabled = False
        self.session_topic_filter = set()
        self.time_left = SESSION_SECONDS
        self._timer_event = None
        self._second_chance_active = False
        self._second_chance_item_id = None
        self._pending_new_card = None
        self._intro_queue = []

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

    def _on_window_focus(self, _window, focused: bool) -> None:
        if focused:
            Clock.schedule_once(self._force_redraw, 0)

    def _force_redraw(self, *_):
        try:
            Window.canvas.ask_update()
        except Exception:
            pass

    def on_resume(self):
        self._force_redraw()
        return True

    def _log_error(self, label: str, exc: Exception | None = None) -> None:
        msg = f"[{datetime.now().isoformat(timespec='seconds')}] {label}"
        if exc is not None:
            msg += f": {exc}"
        self._error_log.append(msg)
        if exc is not None:
            self._last_exception = traceback.format_exc()

    def _ensure_seed_vocab(self) -> None:
        # On desktop, always start from seed data to simplify debugging.
        if not IS_ANDROID and not IS_IOS:
            try:
                os.makedirs(os.path.dirname(self.vocab_path), exist_ok=True)
                with open(SEED_VOCAB_PATH, "rb") as src, open(self.vocab_path, "wb") as dst:
                    dst.write(src.read())
            except Exception as exc:
                self._log_error("seed copy failed", exc)
            return
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

    def _save_settings(self) -> None:
        try:
            _save_json(self.settings_path, self.settings)
        except Exception as exc:
            self._log_error("settings save failed", exc)

    def get_target_languages(self):
        meta = self.vocab.get("meta", {})
        langs = meta.get("target_langs") or []
        if isinstance(langs, str):
            langs = [langs]
        if not langs:
            langs = ["en"]
        return langs

    def ensure_target_language(self, lang: str) -> None:
        if not lang:
            return
        meta = self.vocab.setdefault("meta", {})
        langs = meta.get("target_langs") or []
        if isinstance(langs, str):
            langs = [langs]
        if lang not in langs:
            langs.append(lang)
        meta["target_langs"] = langs
        self._save_vocab()

    def get_learned_topics(self, lang: str):
        lang = (lang or "").strip()
        if not lang:
            return []
        topic_map = {}
        for topic in self.vocab.get("topics", []):
            if topic.get("lang", "en") == lang:
                topic_map[topic.get("id")] = topic.get("name", "")
        learned_ids = set()
        for card in self.vocab.get("cards", []):
            if card.get("lang", "en") != lang:
                continue
            if card.get("id") in self.progress:
                learned_ids.add(card.get("topic"))
        topics = []
        for topic_id in learned_ids:
            name = topic_map.get(topic_id, topic_id or "")
            if name:
                topics.append({"id": topic_id, "name": name})
        topics.sort(key=lambda item: item["name"].lower())
        return topics

    def is_review_topic_filter_enabled(self, lang: str) -> bool:
        return bool(self.settings.get("review_topic_filter_enabled", {}).get(lang, False))

    def get_review_topic_filter(self, lang: str) -> list[str]:
        selected = self.settings.get("review_topics_by_lang", {}).get(lang, [])
        if isinstance(selected, str):
            selected = [selected]
        return [s for s in selected if s]

    def set_review_topic_filter(self, lang: str, topic_ids: list[str], enabled: bool) -> None:
        lang = (lang or "").strip()
        if not lang:
            return
        topics_by_lang = self.settings.setdefault("review_topics_by_lang", {})
        enabled_by_lang = self.settings.setdefault("review_topic_filter_enabled", {})
        if enabled:
            topics_by_lang[lang] = [t for t in topic_ids if t]
            enabled_by_lang[lang] = True
        else:
            topics_by_lang.pop(lang, None)
            enabled_by_lang[lang] = False
        self._save_settings()

    def ensure_topic(self, lang: str, topic: str) -> str:
        topic = topic.strip() or "Allgemein"
        topic_id = _slugify(topic)
        topics = self.vocab.get("topics", [])
        if not any(t.get("id") == topic_id and t.get("lang", "en") == lang for t in topics):
            topics.append({"id": topic_id, "name": topic, "lang": lang})
        self.vocab["topics"] = topics
        self._save_vocab()
        return topic_id

    def get_topics(self, lang: str):
        topics = []
        for topic in self.vocab.get("topics", []):
            if topic.get("lang", "en") == lang:
                topics.append(topic.get("name", ""))
        return [t for t in topics if t]

    def get_topic_name(self, topic_id: str | None, lang: str | None = None) -> str:
        if not topic_id:
            return ""
        for topic in self.vocab.get("topics", []):
            if topic.get("id") != topic_id:
                continue
            if lang and topic.get("lang", "en") != lang:
                continue
            return topic.get("name", "") or topic_id
        return topic_id

    def get_intro_topic_progress(self, lang: str, direction: str) -> list[dict]:
        if not lang:
            return []
        topics = [t for t in self.vocab.get("topics", []) if t.get("lang", "en") == lang]
        topic_names = {t.get("id"): t.get("name", "") for t in topics}
        totals: dict[str, int] = {}
        introduced: dict[str, int] = {}
        for card in self.vocab.get("cards", []):
            if card.get("lang", "en") != lang:
                continue
            topic_id = card.get("topic")
            if not topic_id:
                continue
            totals[topic_id] = totals.get(topic_id, 0) + 1
            if self.progress.get(card.get("id", ""), {}).get(direction) is not None:
                introduced[topic_id] = introduced.get(topic_id, 0) + 1
        items = []
        for topic_id, total in totals.items():
            if total <= 0:
                continue
            done = introduced.get(topic_id, 0)
            percent = int(round((done / total) * 100))
            if percent >= 100:
                continue
            items.append({
                "id": topic_id,
                "name": topic_names.get(topic_id, "") or topic_id,
                "percent": percent,
                "total": total,
                "done": done,
            })
        items.sort(key=lambda it: (it["percent"], it["name"].lower()))
        return items

    def _is_topic_complete(self, topic_id: str, lang: str, direction: str) -> bool:
        if not topic_id or not lang:
            return False
        total = 0
        done = 0
        for card in self.vocab.get("cards", []):
            if card.get("lang", "en") != lang:
                continue
            if card.get("topic") != topic_id:
                continue
            total += 1
            if self.progress.get(card.get("id", ""), {}).get(direction) is not None:
                done += 1
        return total > 0 and done >= total

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

    def _get_card_by_id(self, card_id: str) -> dict | None:
        if not card_id:
            return None
        for card in self.vocab.get("cards", []):
            if card.get("id") == card_id:
                return card
        return None

    def _save_card_mnemonic(self, card_id: str | None, text: str) -> None:
        if not card_id:
            return
        card = self._get_card_by_id(card_id)
        if not card:
            return
        cleaned = (text or "").strip()
        if card.get("mnemonic", "") == cleaned:
            return
        card["mnemonic"] = cleaned
        self._save_vocab()

    def show_training_setup(self) -> None:
        self.sm.current = "setup"

    def show_vocab(self) -> None:
        self.sm.current = "vocab"

    def show_calendar(self) -> None:
        self.sm.current = "calendar"

    def show_menu(self) -> None:
        self.sm.current = "menu"

    def open_menu(self, *_):
        layout = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(10))
        layout.add_widget(Button(text="Lizenz", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                                 on_release=lambda *_: self._show_license()))
        layout.add_widget(Button(text="Unterstütze mich", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                                 on_release=lambda *_: self._open_support()))
        layout.add_widget(Button(text="Datenbank Export", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                                 on_release=lambda *_: self._export_backup()))
        layout.add_widget(Button(text="Datenbank Import", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                                 on_release=lambda *_: self._import_backup_prompt()))
        layout.add_widget(Button(text="Debug report", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                                 on_release=lambda *_: self._show_debug_report()))
        layout.add_widget(Button(text="Schließen", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                                 on_release=lambda *_: popup.dismiss()))
        popup = _styled_popup(title="Menü", content=layout, size_hint=(0.8, 0.7))
        popup.open()

    def _show_license(self) -> None:
        try:
            text = _read_text(os.path.join(os.path.dirname(__file__), "License.txt"))
        except Exception as exc:
            text = f"License not available: {exc}"
        box = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(6))
        box.add_widget(_styled_text_input(text=text, readonly=True))
        box.add_widget(Button(text="Schließen", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                              on_release=lambda *_: popup.dismiss()))
        popup = _styled_popup(title="Lizenz", content=box, size_hint=(0.9, 0.9))
        popup.open()

    def _open_support(self) -> None:
        import webbrowser
        webbrowser.open(SUPPORT_URL)

    def _export_backup(self) -> None:
        if filechooser is not None and hasattr(filechooser, "save_file"):
            try:
                paths = filechooser.save_file(title="Datenbank Export", path=os.path.expanduser("~"),
                                              filters=[("YAML", "*.yaml")])
                if paths:
                    self._export_backup_to(paths[0])
                    return
            except Exception as exc:
                self._log_error("filechooser save failed", exc)
        if not IS_ANDROID:
            default_name = self._default_backup_filename()
            tk_path = _tk_save_file("Datenbank Export", os.path.expanduser("~"), default_name)
            if tk_path:
                self._export_backup_to(tk_path)
                return
        if filechooser is not None and hasattr(filechooser, "choose_dir"):
            self._export_backup_choose_dir()
            return
        self._export_backup_prompt()

    def _default_backup_filename(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}.yaml"

    def _export_backup_choose_dir(self) -> None:
        try:
            dirs = filechooser.choose_dir(title="Datenbank Export", path=os.path.expanduser("~"))
            if not dirs:
                self._export_backup_prompt()
                return
            folder = _normalize_path(dirs[0])
            filename = self._default_backup_filename()
            path = os.path.join(folder, filename)
            self._export_backup_to(path, show_path=True)
        except Exception as exc:
            self._log_error("filechooser choose_dir failed", exc)
            self._export_backup_prompt()

    def _export_backup_prompt(self) -> None:
        default_path = os.path.join(self.backup_dir, self._default_backup_filename())
        box = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(8))
        box.add_widget(_styled_label("Pfad für Exportdatei"))
        path_input = _styled_text_input(multiline=False, text=default_path)
        box.add_widget(path_input)

        def do_export(_):
            popup.dismiss()
            self._export_backup_to(path_input.text.strip(), show_path=True)

        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="Exportieren", on_release=do_export))
        btn_row.add_widget(Button(text="Abbrechen", on_release=lambda *_: popup.dismiss()))
        box.add_widget(btn_row)
        popup = _styled_popup(title="Datenbank Export", content=_make_scrollable(box), size_hint=(0.9, 0.5))
        popup.open()

    def _export_backup_fallback(self) -> None:
        path = os.path.join(self.backup_dir, self._default_backup_filename())
        self._export_backup_to(path, show_path=True)

    def _export_backup_to(self, path: str, show_path: bool = False) -> None:
        payload = {
            "meta": {"created": datetime.now().isoformat(timespec="seconds")},
            "vocab": self.vocab,
            "progress": self.progress,
            "training_log": self.training_log,
        }
        try:
            path = _normalize_path(path.strip())
            path = _ensure_yaml_extension(path)
            if _is_content_uri(path):
                data = _dump_yaml_bytes(payload)
                _android_write_uri(path, data)
                text = "Export erfolgreich."
            else:
                dir_path = os.path.dirname(path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                _save_yaml(path, payload)
                text = f"Gespeichert:\n{path}" if show_path else "Export erfolgreich."
            _styled_popup(title="Datenbank Export", content=Label(text=text), size_hint=(0.9, 0.4)).open()
        except Exception as exc:
            self._log_error("backup export failed", exc)
            _styled_popup(title="Datenbank Export", content=Label(text=f"Fehler: {exc}"), size_hint=(0.9, 0.4)).open()

    def _import_backup_prompt(self) -> None:
        if filechooser is not None and hasattr(filechooser, "open_file"):
            try:
                paths = filechooser.open_file(title="Datenbank Import", path=os.path.expanduser("~"),
                                              filters=[("YAML", "*.yaml")], multiple=False)
                if paths:
                    self._import_backup(paths[0])
                return
            except Exception as exc:
                self._log_error("filechooser open failed", exc)

        box = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(8))
        box.add_widget(_styled_label("Pfad zur YAML-Datei"))
        path_input = _styled_text_input(multiline=False, text="")
        box.add_widget(path_input)

        def do_import(_):
            popup.dismiss()
            self._import_backup(path_input.text.strip())

        btn_row = BoxLayout(size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), spacing=_ui(8))
        btn_row.add_widget(Button(text="Importieren", on_release=do_import))
        btn_row.add_widget(Button(text="Abbrechen", on_release=lambda *_: popup.dismiss()))
        box.add_widget(btn_row)
        popup = _styled_popup(title="Datenbank Import", content=_make_scrollable(box), size_hint=(0.9, 0.5))
        popup.open()

    def _import_backup(self, path: str) -> None:
        try:
            path = _normalize_path(path.strip())
            if _is_content_uri(path):
                raw = _android_read_uri(path)
                data = _load_yaml_bytes(raw)
            else:
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
            _styled_popup(title="Datenbank Import", content=Label(text="Import erfolgreich."), size_hint=(0.6, 0.4)).open()
        except Exception as exc:
            self._log_error("backup import failed", exc)
            _styled_popup(title="Datenbank Import", content=Label(text=f"Import-Fehler: {exc}"), size_hint=(0.8, 0.4)).open()

    def _show_debug_report(self) -> None:
        lines = ["JonMem Debug Report", f"Version: {__version__}", f"Platform: {kivy_platform}"]
        if self._error_log:
            lines.append("Errors:")
            lines.extend(self._error_log)
        if self._last_exception:
            lines.append("\nLast exception:\n" + self._last_exception)
        box = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(6))
        box.add_widget(_styled_text_input(text="\n".join(lines), readonly=True))
        box.add_widget(Button(text="Schließen", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                              on_release=lambda *_: popup.dismiss()))
        popup = _styled_popup(title="Debug report", content=box, size_hint=(0.95, 0.95))
        popup.open()

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
            _styled_popup(title="Vokabeln", content=Label(text="Bitte zuerst eine Sprache wählen."), size_hint=(0.6, 0.3)).open()
            return
        if not de or not en:
            _styled_popup(title="Vokabeln", content=Label(text="Deutsch und Zielsprache müssen gesetzt sein."),
                          size_hint=(0.6, 0.3)).open()
            return
        topic = topic.strip() or "Allgemein"
        topic_id = self.ensure_topic(lang, topic)
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
            "mnemonic": "",
        })
        self.vocab["cards"] = cards
        meta = self.vocab.setdefault("meta", {})
        target_langs = meta.get("target_langs") or []
        if isinstance(target_langs, str):
            target_langs = [target_langs]
        if lang not in target_langs:
            target_langs.append(lang)
        meta["target_langs"] = target_langs
        self._save_vocab()
        _styled_popup(title="Vokabeln", content=Label(text="Gespeichert."), size_hint=(0.4, 0.3)).open()

    def update_card(self, card_id: str, de: str, en: str, hint_de: str, hint_en: str) -> None:
        if not card_id:
            return
        cards = self.vocab.get("cards", [])
        for card in cards:
            if card.get("id") == card_id:
                card["de"] = de
                card["en"] = en
                card["hint_de_to_en"] = hint_de
                card["hint_en_to_de"] = hint_en
                break
        self.vocab["cards"] = cards
        self._save_vocab()

    def delete_card(self, card_id: str) -> None:
        if not card_id:
            return
        cards = self.vocab.get("cards", [])
        cards = [card for card in cards if card.get("id") != card_id]
        self.vocab["cards"] = cards
        if card_id in self.progress:
            self.progress.pop(card_id, None)
            _save_json(self.progress_path, self.progress)
        self._save_vocab()

    def start_training(self, mode: str, direction: str, lang: str,
                       topic_filter: list[str] | None = None, topic_filter_enabled: bool = False) -> None:
        self.session_mode = mode
        self.session_direction = direction
        self.session_lang = lang or "en"
        self.session_topic_filter_enabled = bool(topic_filter_enabled)
        self.session_topic_filter = set(topic_filter or [])
        self.session_intro_topic = None
        self._intro_completed_before = False
        if mode == "introduce":
            intro_topics = self.get_intro_topic_progress(self.session_lang, self.session_direction)
            if not intro_topics:
                _styled_popup(title="Training", content=Label(text="Alle Kategorien sind eingeführt."),
                              size_hint=(0.7, 0.3)).open()
                return
            topic_id = intro_topics[0]["id"]
            self.session_intro_topic = topic_id
            self._intro_completed_before = self._is_topic_complete(
                topic_id, self.session_lang, self.session_direction
            )
            unseen_cards = self._get_unseen_cards(topic_id=topic_id)
            rng = random
            rng.shuffle(unseen_cards)
            unique_limit = max(1, SESSION_MAX_ITEMS // max(1, INTRODUCE_REPEAT_COUNT))
            unseen_items = [self._card_to_item(card) for card in unseen_cards[:unique_limit]]
            if len(unseen_items) < unique_limit:
                needed = unique_limit - len(unseen_items)
                review_fill = training.build_session_items(
                    self.vocab.get("cards", []),
                    self.progress,
                    mode="review",
                    direction=self.session_direction,
                    lang=self.session_lang,
                    topic_filter_enabled=True,
                    topic_filter={topic_id},
                    max_items=needed,
                    introduce_repeat_count=INTRODUCE_REPEAT_COUNT,
                    max_stage=MAX_STAGE,
                    pyramid_stage_weights=PYRAMID_STAGE_WEIGHTS,
                    rng=random,
                )
                unique_items = unseen_items + review_fill
            else:
                unique_items = unseen_items
            if not unique_items:
                _styled_popup(title="Training", content=Label(text="Keine passenden Karten gefunden."),
                              size_hint=(0.6, 0.3)).open()
                return
            session = unique_items * max(1, INTRODUCE_REPEAT_COUNT)
            self.session_items = training.shuffle_avoid_adjacent(session, "id", random)[:SESSION_MAX_ITEMS]
            self._intro_queue = list(unseen_items)
        else:
            self.session_items = self._build_session_items(mode, direction)
        if not self.session_items:
            _styled_popup(title="Training", content=Label(text="Keine passenden Karten gefunden."), size_hint=(0.6, 0.3)).open()
            return
        self.session_index = 0
        self.session_correct = 0
        self.time_left = SESSION_SECONDS
        self.session_start = datetime.now()
        self._second_chance_active = False
        self._second_chance_item_id = None
        self._pending_new_card = None
        self.sm.current = "train"
        if mode == "introduce":
            if not self._intro_queue:
                self._intro_queue = list(self.session_items)
            self._show_next_intro_card()
        else:
            self._intro_queue = []
            self._start_timer()

    def _build_session_items(self, mode: str, direction: str):
        return training.build_session_items(
            self.vocab.get("cards", []),
            self.progress,
            mode=mode,
            direction=direction,
            lang=self.session_lang,
            topic_filter_enabled=self.session_topic_filter_enabled,
            topic_filter=set(self.session_topic_filter),
            max_items=SESSION_MAX_ITEMS,
            introduce_repeat_count=INTRODUCE_REPEAT_COUNT,
            max_stage=MAX_STAGE,
            pyramid_stage_weights=PYRAMID_STAGE_WEIGHTS,
        )

    def _card_to_item(self, card: dict, prog: dict | None = None) -> dict:
        stage = 1
        if prog is None:
            prog = self.progress.get(card.get("id", ""), {}).get(self.session_direction)
        if prog is not None:
            stage = int(prog.get("stage", 1))
        return {
            "id": card.get("id"),
            "prompt": card.get("de") if self.session_direction == "de_to_en" else card.get("en"),
            "answer": card.get("en") if self.session_direction == "de_to_en" else card.get("de"),
            "hint": card.get("hint_de_to_en") if self.session_direction == "de_to_en" else card.get("hint_en_to_de"),
            "de": card.get("de", ""),
            "en": card.get("en", ""),
            "hint_de_to_en": card.get("hint_de_to_en", ""),
            "hint_en_to_de": card.get("hint_en_to_de", ""),
            "mnemonic": card.get("mnemonic", ""),
            "stage": stage,
            "topic": card.get("topic"),
            "lang": card.get("lang", "en"),
        }

    def _get_unseen_cards(self, *, exclude_ids: set[str] | None = None, topic_id: str | None = None) -> list[dict]:
        exclude_ids = exclude_ids or set()
        cards = training.list_unseen_cards(
            self.vocab.get("cards", []),
            self.progress,
            direction=self.session_direction,
            lang=self.session_lang,
        )
        if topic_id:
            cards = [card for card in cards if card.get("topic") == topic_id]
        return [card for card in cards if card.get("id") not in exclude_ids]

    def _queue_new_intro_card(self) -> None:
        existing_ids = {item.get("id") for item in self.session_items if item.get("id")}
        topic_id = self.session_intro_topic if self.session_mode == "introduce" else None
        unseen_cards = self._get_unseen_cards(exclude_ids=existing_ids, topic_id=topic_id)
        if not unseen_cards:
            return
        new_item = self._card_to_item(unseen_cards[0])
        self.session_items.append(new_item)
        self._pending_new_card = new_item

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
            level = int(item.get("stage", 1) or 1)
            topic_name = self.get_topic_name(item.get("topic"), self.session_lang)
            self.screen_train.category_label.text = f"Kategorie: {topic_name or '-'}"
            self.screen_train.level_label.text = f"Level {level}"
            self.screen_train._card_color.rgba = _level_bg_color(level)
        else:
            self.screen_train.prompt_label.text = ""
            self.screen_train.category_label.text = "Kategorie: -"
            self.screen_train.level_label.text = "Level 1"
            self.screen_train._card_color.rgba = CARD_BG

    def submit_answer(self, text: str) -> None:
        if self.session_index >= len(self.session_items):
            return
        item = self.session_items[self.session_index]
        expected = item.get("answer", "")
        analysis = training.analyze_answer(text, expected)
        level = int(item.get("stage", 1) or 1)

        if self._second_chance_active and self._second_chance_item_id == item.get("id"):
            correct = analysis.get("correct", False)
            if correct:
                self.session_correct += 1
                if self._sound_success is not None:
                    self._sound_success.play()
                prev_stage, new_stage = self._update_progress(item["id"], True)
                if self.session_mode == "introduce" and prev_stage == 1 and new_stage == 2:
                    self._queue_new_intro_card()
            else:
                self._update_progress(item["id"], False)

            # Pause timer while showing feedback
            if self._timer_event is not None:
                self._timer_event.cancel()
                self._timer_event = None

            self._second_chance_active = False
            self._second_chance_item_id = None
            self._show_answer_popup(item, correct, given_text=text)
            self.screen_train.answer_input.text = ""
            return

        if analysis.get("correct", False):
            self.session_correct += 1
            if self._sound_success is not None:
                self._sound_success.play()
            prev_stage, new_stage = self._update_progress(item["id"], True)
            if self.session_mode == "introduce" and prev_stage == 1 and new_stage == 2:
                self._queue_new_intro_card()

            # Pause timer while showing feedback
            if self._timer_event is not None:
                self._timer_event.cancel()
                self._timer_event = None

            self._show_answer_popup(item, True)
            self.screen_train.answer_input.text = ""
            return

        second_chance, hint_lines = self._second_chance_hint(level, analysis, expected)
        if second_chance:
            self._second_chance_active = True
            self._second_chance_item_id = item.get("id")
            if self._sound_almost is not None:
                self._sound_almost.play()

            # Pause timer while showing feedback
            if self._timer_event is not None:
                self._timer_event.cancel()
                self._timer_event = None

            self._show_second_chance_popup(hint_lines)
            return

        self._update_progress(item["id"], False)

        # Pause timer while showing feedback
        if self._timer_event is not None:
            self._timer_event.cancel()
            self._timer_event = None

        self._show_answer_popup(item, False, given_text=text)
        self.screen_train.answer_input.text = ""

    def _show_answer_popup(self, item: dict, correct: bool, given_text: str = "") -> None:
        status = "Richtig" if correct else "Falsch"
        color = "00cc66" if correct else "ff4444"
        de_text = item.get("de", "")
        en_text = item.get("en", "")
        hint_de = item.get("hint_de_to_en", "")
        hint_en = item.get("hint_en_to_de", "")
        mnemonic_text = item.get("mnemonic", "")
        if not mnemonic_text:
            card = self._get_card_by_id(item.get("id"))
            if card:
                mnemonic_text = card.get("mnemonic", "")

        layout = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(10))
        layout.add_widget(Label(text=f"[color={color}]{status}[/color]", markup=True, size_hint_y=None, height=_ui(28)))
        if not correct and given_text:
            safe_given = escape_markup(given_text)
            layout.add_widget(Label(text=f"Deine Eingabe: [s]{safe_given}[/s]",
                                    markup=True, size_hint_y=None, height=_ui(26)))
        layout.add_widget(Label(text=f"Deutsch: {de_text}"))
        lang = (self.session_lang or "en").upper()
        layout.add_widget(Label(text=f"Zielsprache ({lang}): {en_text}"))
        layout.add_widget(Label(text="Eselsbrücke/Notiz (optional)"))
        mnemonic_input = _styled_text_input(text=mnemonic_text, multiline=True, size_hint_y=None, height=_ui(110))
        layout.add_widget(mnemonic_input)
        if hint_de:
            layout.add_widget(Label(text=f"Eselsbrücke DE → ZS: {hint_de}"))
        if hint_en:
            layout.add_widget(Label(text=f"Eselsbrücke ZS → DE: {hint_en}"))

        def _next(_):
            self._save_card_mnemonic(item.get("id"), mnemonic_input.text)
            item["mnemonic"] = (mnemonic_input.text or "").strip()
            popup.dismiss()
            self.session_index += 1
            if self.session_index >= len(self.session_items):
                self.end_training(cancelled=False)
            else:
                if self._pending_new_card is not None:
                    pending = self._pending_new_card
                    self._pending_new_card = None
                    self._show_new_card_popup(pending, resume_timer=True)
                else:
                    self._start_timer()
                    self.update_training_view()

        layout.add_widget(Button(text="OK", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), on_release=_next))
        popup = _styled_popup(title="Lösung", content=layout, size_hint=(0.9, 0.8))
        popup.open()

    def _show_second_chance_popup(self, hint_lines: list[str]) -> None:
        layout = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(10))
        for line in hint_lines:
            layout.add_widget(Label(text=line))

        def _resume(_):
            popup.dismiss()
            self._start_timer()
            self.update_training_view()

        layout.add_widget(Button(text="OK", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), on_release=_resume))
        popup = _styled_popup(title="Fast richtig....", content=layout, size_hint=(0.8, 0.4))
        popup.open()

    def _show_new_card_popup(self, item: dict, *, resume_timer: bool) -> None:
        if self._sound_new_card is not None:
            self._sound_new_card.play()
        de_text = item.get("de", "")
        en_text = item.get("en", "")
        hint_de = item.get("hint_de_to_en", "")
        hint_en = item.get("hint_en_to_de", "")

        layout = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(10))
        layout.add_widget(Label(text=f"Deutsch: {de_text}"))
        lang = (self.session_lang or "en").upper()
        layout.add_widget(Label(text=f"Zielsprache ({lang}): {en_text}"))
        if hint_de:
            layout.add_widget(Label(text=f"Eselsbrücke DE → ZS: {hint_de}"))
        if hint_en:
            layout.add_widget(Label(text=f"Eselsbrücke ZS → DE: {hint_en}"))

        def _close(_):
            popup.dismiss()
            if resume_timer:
                self._start_timer()
                self.update_training_view()

        layout.add_widget(Button(text="OK", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), on_release=_close))
        popup = _styled_popup(title="Neue Karte!", content=layout, size_hint=(0.9, 0.7))
        popup.open()

    def _show_next_intro_card(self) -> None:
        if not self._intro_queue:
            self._start_timer()
            self.update_training_view()
            return
        item = self._intro_queue.pop(0)

        def _after_close(_):
            popup.dismiss()
            self._show_next_intro_card()

        if self._sound_new_card is not None:
            self._sound_new_card.play()
        de_text = item.get("de", "")
        en_text = item.get("en", "")
        hint_de = item.get("hint_de_to_en", "")
        hint_en = item.get("hint_en_to_de", "")
        layout = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(10))
        layout.add_widget(Label(text=f"Deutsch: {de_text}"))
        lang = (self.session_lang or "en").upper()
        layout.add_widget(Label(text=f"Zielsprache ({lang}): {en_text}"))
        if hint_de:
            layout.add_widget(Label(text=f"Eselsbrücke DE → ZS: {hint_de}"))
        if hint_en:
            layout.add_widget(Label(text=f"Eselsbrücke ZS → DE: {hint_en}"))
        layout.add_widget(Button(text="OK", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT), on_release=_after_close))
        popup = _styled_popup(title="Neue Karte!", content=layout, size_hint=(0.9, 0.7))
        popup.open()

    def _second_chance_hint(self, level: int, analysis: dict, expected: str) -> tuple[bool, list[str]]:
        if level >= 4:
            return False, []
        if not analysis.get("given_norm") or not analysis.get("expected_norm"):
            return False, []
        max_letters = 2 if level == 3 else 4
        letter_errors = int(analysis.get("letter_errors", 0))
        accent_errors = int(analysis.get("accent_errors", 0))
        punct_errors = int(analysis.get("punct_errors", 0))
        case_only = bool(analysis.get("case_only", False))
        missing_word = bool(analysis.get("missing_word", False))

        if letter_errors > max_letters:
            return False, []

        hints: list[str] = []
        if level == 3:
            if case_only:
                hints.append("Achte auf Groß/Kleinschreibung.")
            elif letter_errors > 0:
                hints.append("guck noch mal genau")
            else:
                hints.append("Irgendwas stimmt noch nicht.")
            return True, hints

        if case_only:
            hints.append("Achte auf Groß/Kleinschreibung.")
        elif letter_errors > 0:
            hints.append("guck noch mal genau")

        if accent_errors > 0:
            if "ñ" in expected or "Ñ" in expected:
                hints.append("Achte auf die Tilde über dem n.")
            else:
                hints.append("Achte auf die Akzente.")

        if punct_errors > 0:
            if any(ch in expected for ch in ("'", "’", "´")):
                hints.append("Achte auf das Apostroph.")
            else:
                hints.append("Achte auf die Satzzeichen.")

        if level == 1 and missing_word:
            hints.append("Hier fehlt noch ein Wort.")

        if letter_errors > 0 and (accent_errors > 0 or punct_errors > 0):
            total_errors = letter_errors + accent_errors + punct_errors
            hints.append(f"Es gibt noch weitere Fehler (insgesamt {total_errors}).")

        return True, hints

    def _update_progress(self, card_id: str, correct: bool) -> tuple[int, int]:
        entry = self.progress.setdefault(card_id, {})
        dir_entry = entry.setdefault(self.session_direction, {"stage": 1})
        stage = int(dir_entry.get("stage", 1))
        new_stage = training.compute_next_stage(stage, correct, MAX_STAGE)
        dir_entry["stage"] = new_stage
        dir_entry["last_seen"] = datetime.now().isoformat(timespec="seconds")
        dir_entry["last_result"] = bool(correct)
        _save_json(self.progress_path, self.progress)
        return stage, new_stage

    def end_training(self, cancelled: bool) -> None:
        if self._timer_event is not None:
            self._timer_event.cancel()
            self._timer_event = None
        if cancelled:
            self.sm.current = "menu"
            return
        if self.session_mode == "introduce" and self.time_left <= 0:
            changed = False
            seen_ids = {item.get("id") for item in self.session_items if item.get("id")}
            for card_id in seen_ids:
                entry = self.progress.get(card_id, {})
                dir_entry = entry.get(self.session_direction)
                if dir_entry and int(dir_entry.get("stage", 1)) == 1:
                    entry.pop(self.session_direction, None)
                    changed = True
                if entry == {}:
                    self.progress.pop(card_id, None)
            if changed:
                _save_json(self.progress_path, self.progress)
        total = len(self.session_items)
        summary = f"{self.session_correct} von {total} richtig."
        self._append_training_log(total)
        if self.session_mode == "introduce" and self.session_intro_topic:
            now_complete = self._is_topic_complete(
                self.session_intro_topic, self.session_lang, self.session_direction
            )
            if now_complete and not self._intro_completed_before:
                topic_name = self.get_topic_name(self.session_intro_topic, self.session_lang)
                _styled_popup(
                    title="Erfolg",
                    content=Label(text=f"Kategorie abgeschlossen: {topic_name}"),
                    size_hint=(0.7, 0.3),
                ).open()
        _styled_popup(title="Training", content=Label(text=summary), size_hint=(0.6, 0.4)).open()
        self.sm.current = "menu"

    def show_session_pyramid(self) -> None:
        if not self.session_items:
            _styled_popup(title="Pyramide", content=Label(text="Keine Session aktiv."), size_hint=(0.6, 0.3)).open()
            return
        stages = {i: [] for i in range(1, MAX_STAGE + 1)}
        seen_ids = set()
        for item in self.session_items:
            item_id = item.get("id")
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            prog = self.progress.get(item["id"], {}).get(self.session_direction, {})
            stage = int(prog.get("stage", 1))
            stages.setdefault(stage, []).append(item.get("prompt", ""))

        layout = BoxLayout(orientation="vertical", spacing=_ui(6), padding=_ui(10))
        scroll = ScrollView()
        inner = BoxLayout(orientation="vertical", size_hint_y=None, spacing=_ui(4))
        inner.bind(minimum_height=inner.setter("height"))

        for stage in range(MAX_STAGE, 0, -1):
            inner.add_widget(Label(text=f"Stufe {stage}", size_hint_y=None, height=_ui(24), bold=True))
            for prompt in stages.get(stage, []):
                inner.add_widget(Label(text=f"• {prompt}", size_hint_y=None, height=_ui(22), halign="left"))
        scroll.add_widget(inner)
        layout.add_widget(scroll)
        layout.add_widget(Button(text="Schließen", size_hint_y=None, height=_ui(BASE_BUTTON_HEIGHT),
                                 on_release=lambda *_: popup.dismiss()))
        popup = _styled_popup(title="Pyramide der Session", content=layout, size_hint=(0.9, 0.9))
        popup.open()

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
            if not day:
                continue
            day_entry = counts.setdefault(day, {"introduce": 0, "review": 0})
            mode = entry.get("mode")
            if mode == "introduce":
                day_entry["introduce"] += 1
            elif mode == "review":
                day_entry["review"] += 1
            else:
                day_entry["review"] += 1
        return counts


if __name__ == "__main__":
    JonMemApp().run()
