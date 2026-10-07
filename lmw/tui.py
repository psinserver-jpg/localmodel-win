"""Claude-Code-style terminal UI: boxed input, slash-command completion, Shift+Tab mode cycling,
arrow-key choice menus. Uses prompt_toolkit (https://github.com/prompt-toolkit/python-prompt-toolkit)
when installed; otherwise falls back to plain input() so lmw always works.

Both the input box and the choice menu can also be answered from the website: an external
queue is watched and its first item ends the prompt (as if typed).
"""

from __future__ import annotations

import queue
import sys
import threading
from typing import Callable, List, Optional, Sequence, Tuple

try:  # optional dependency
    from prompt_toolkit.application import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.formatted_text import ANSI, FormattedText, to_formatted_text
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import HSplit, Layout, Window
    from prompt_toolkit.layout.containers import ConditionalContainer, Float, FloatContainer
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.layout.menus import CompletionsMenu
    from prompt_toolkit.layout.processors import BeforeInput
    from prompt_toolkit.styles import Style
    from prompt_toolkit.widgets import Frame
    from prompt_toolkit.widgets.base import Border
    Border.TOP_LEFT, Border.TOP_RIGHT, Border.BOTTOM_LEFT, Border.BOTTOM_RIGHT = "╭", "╮", "╰", "╯"
    HAVE_PT = True
except Exception:  # pragma: no cover - fallback path
    HAVE_PT = False

ACCENT = "#d97a4a"
STYLE = None
if HAVE_PT:
    STYLE = Style.from_dict({
        "frame.border": "#5c5b56",
        "frame.border.focused": ACCENT,
        "prompt": "bold " + ACCENT,
        "hint": "#8a8984",
        "mode": "bold " + ACCENT,
        "choice": "",
        "choice.selected": "bold " + ACCENT,
        "completion-menu.completion": "bg:#2a2926 #ecebe6",
        "completion-menu.completion.current": "bg:%s #1c1b19" % ACCENT,
        "completion-menu.meta.completion": "bg:#2a2926 #a3a29c",
        "completion-menu.meta.completion.current": "bg:%s #1c1b19" % ACCENT,
    })

_history = None


def available() -> bool:
    return HAVE_PT and sys.stdin.isatty() and sys.stdout.isatty()


class _SlashCompleter(Completer if HAVE_PT else object):  # type: ignore[misc]
    def __init__(self, commands: Sequence[Tuple[str, str]]):
        self.commands = list(commands)

    def get_completions(self, document, complete_event):  # noqa: D401
        text = document.text_before_cursor
        if not text.startswith("/") or " " in text:
            return
        for cmd, desc in self.commands:
            if cmd.startswith(text):
                yield Completion(cmd, start_position=-len(text), display_meta=desc)


def _watch(app, external: Optional["queue.Queue"], done: threading.Event, box: dict) -> None:
    """End the running prompt when something arrives from the website."""
    while external is not None and not done.is_set():
        try:
            item = external.get(timeout=0.2)
        except queue.Empty:
            continue
        box["external"] = item
        try:
            app.loop.call_soon_threadsafe(lambda: app.exit(result=None))
        except Exception:
            pass
        return


def input_box(commands: Sequence[Tuple[str, str]], hints: Callable[[], List[Tuple[str, str]]],
              on_shift_tab: Optional[Callable[[], None]] = None,
              external: Optional["queue.Queue"] = None, default: str = "") -> Tuple[str, str]:
    """Boxed multi-line input. Returns (source, text): source "key" or whatever the external item says."""
    global _history
    if _history is None:
        _history = InMemoryHistory()
    buf = Buffer(multiline=True, completer=_SlashCompleter(commands), complete_while_typing=True,
                 history=_history, document=Document(default, len(default)))
    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        st = buf.complete_state
        if st and st.completions:
            c = st.current_completion or st.completions[0]
            if c.text != buf.text:  # Enter on "/he" runs "/help", like Claude Code
                buf.apply_completion(c)
        event.app.exit(result=buf.text)

    @kb.add("escape", "enter")  # Alt+Enter / Esc,Enter: new line
    @kb.add("c-j")
    def _(event):
        buf.insert_text("\n")

    @kb.add("s-tab")
    def _(event):
        if on_shift_tab:
            on_shift_tab()
        event.app.invalidate()

    @kb.add("c-c")
    def _(event):
        if buf.text:
            buf.reset()
        else:
            event.app.exit(exception=KeyboardInterrupt())

    @kb.add("c-d")
    def _(event):
        if not buf.text:
            event.app.exit(exception=EOFError())

    body = Window(BufferControl(buf, input_processors=[BeforeInput(FormattedText([("class:prompt", "> ")]))]),
                  height=Dimension(min=1, max=12), wrap_lines=True, dont_extend_height=True)
    hint_win = Window(FormattedTextControl(lambda: FormattedText(hints())), height=1)
    root = FloatContainer(HSplit([Frame(body), hint_win]),
                          floats=[Float(xcursor=True, ycursor=True, content=CompletionsMenu(max_height=10))])
    app = Application(layout=Layout(root, focused_element=body), key_bindings=kb, style=STYLE,
                      full_screen=False, mouse_support=False, erase_when_done=True)
    done, box = threading.Event(), {}
    threading.Thread(target=_watch, args=(app, external, done, box), daemon=True).start()
    try:
        text = app.run()
    finally:
        done.set()
    if "external" in box:
        src, ext = box["external"]
        return src, ext
    if text and text.strip():
        _history.append_string(text)
    return "key", text or ""


def choose(title_lines: List[str], options: List[str], external: Optional["queue.Queue"] = None,
           accept_external: Optional[Callable[[object], Optional[int]]] = None) -> Tuple[int, str]:
    """Arrow-key / number menu. Returns (index, source). Esc picks the last option (= no)."""
    state = {"i": 0}
    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _(event):
        state["i"] = (state["i"] - 1) % len(options)

    @kb.add("down")
    @kb.add("j")
    @kb.add("tab")
    def _(event):
        state["i"] = (state["i"] + 1) % len(options)

    @kb.add("enter")
    def _(event):
        event.app.exit(result=state["i"])

    for n in range(1, len(options) + 1):
        @kb.add(str(n))
        def _(event, n=n):
            event.app.exit(result=n - 1)

    @kb.add("escape")
    @kb.add("c-c")
    def _(event):
        event.app.exit(result=len(options) - 1)

    def render():
        out = []
        for line in title_lines:
            out.extend(to_formatted_text(ANSI(line + "\n")))
        for i, o in enumerate(options):
            sel = i == state["i"]
            out.append(("class:choice.selected" if sel else "class:choice", ("❯ " if sel else "  ") + "%d. %s\n" % (i + 1, o)))
        out.append(("class:hint", "  ↑↓ 선택 · Enter 확인 · 1-%d 바로 선택 · Esc 아니요" % len(options)))
        return FormattedText(out)

    app = Application(layout=Layout(Frame(Window(FormattedTextControl(render), dont_extend_height=True))),
                      key_bindings=kb, style=STYLE, full_screen=False, erase_when_done=False)
    done, box = threading.Event(), {}

    def watch():
        while external is not None and not done.is_set():
            try:
                item = external.get(timeout=0.2)
            except queue.Empty:
                continue
            idx = accept_external(item) if accept_external else None
            if idx is None:
                box.setdefault("requeue", []).append(item)  # not an answer to this menu
                continue
            if idx < 0:
                continue  # stale answer to an older menu
            box["external"] = idx
            try:
                app.loop.call_soon_threadsafe(lambda: app.exit(result=idx))
            except Exception:
                pass
            return

    threading.Thread(target=watch, daemon=True).start()
    try:
        idx = app.run()
    finally:
        done.set()
    for item in box.get("requeue", []):
        external.put(item)  # type: ignore[union-attr]
    return idx, ("web" if "external" in box else "key")
