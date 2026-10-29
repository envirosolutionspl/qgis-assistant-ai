# -*- coding: utf-8 -*-
"""Kolorystyka w konwencji wtyczek EnviroSolutions (zieleń #4c6e4f).

Jak w wersji 0.1. Belki zwijanych sekcji rozróżniają odcienie tej samej
zieleni: Polecenie najmocniejszy, Wynik pośredni, Dziennik najjaśniejszy.
"""

LIGHT = {
    "primary": "#4c6e4f", "primary_hover": "#5b8260",
    "primary_pressed": "#3d5a40",
    "primary_soft": "#e8efe8", "primary_text": "#3b5a3e",
    "heading": "#3b5a3e",
    "bg": "#ffffff", "panel": "#f6f8f6", "card": "#ffffff", "input": "#ffffff",
    "text": "#23282a", "muted": "#6b7572", "border": "#d6ded6",
    "border_strong": "#b9c7ba",
    "disabled_bg": "#c9d3ca", "disabled_text": "#f4f6f4",
    "warn": "#c98a1a", "warn_text": "#c98a1a", "warn_bg": "#fff8ea",
    "warn_border": "#f0dcb0",
    "error": "#b23b3b", "error_bg": "#fdf0f0", "error_border": "#efc9c9",
    "ok": "#3f7d46", "code_bg": "#eef3ee", "running": "#2f7fb5",
    "row_wait": "#fff8ea", "row_error": "#fdf0f0", "accent": "#4c6e4f",
    "on_primary": "#ffffff",
    # belki sekcji: tło / obramowanie karty / tytuł
    "head_cmd": "#b9c7ba", "edge_cmd": "#b9c7ba", "title_cmd": "#23282a",
    "head_res": "#d6ded6", "edge_res": "#d6ded6", "title_res": "#23282a",
    "head_log": "#e8efe8", "edge_log": "#d6ded6", "title_log": "#3b5a3e",
    "logo_bg": "transparent", "logo_pad": "0px",
}
DARK = {
    "primary": "#6f9c73", "primary_hover": "#7fae83",
    "primary_pressed": "#5b8260",
    "primary_soft": "#2c3a2d", "primary_text": "#a9cfac",
    "heading": "#a9cfac",
    "bg": "#2b2d2e", "panel": "#303334", "card": "#262829", "input": "#1f2122",
    "text": "#e6e9e7", "muted": "#9aa4a0", "border": "#44494a",
    "border_strong": "#5a6162",
    "disabled_bg": "#3e4442", "disabled_text": "#8a918e",
    "warn": "#e0a940", "warn_text": "#e0a940", "warn_bg": "#3a3222",
    "warn_border": "#5a4a28",
    "error": "#e07070", "error_bg": "#3a2626", "error_border": "#5a3434",
    "ok": "#7fbf86", "code_bg": "#1f2a20", "running": "#6fb3e0",
    "row_wait": "#3a3222", "row_error": "#3a2626", "accent": "#6f9c73",
    "on_primary": "#ffffff",
    "head_cmd": "#4c6e4f", "edge_cmd": "#4c6e4f", "title_cmd": "#ffffff",
    "head_res": "#3d5a40", "edge_res": "#3d5a40", "title_res": "#e6e9e7",
    "head_log": "#2c3a2d", "edge_log": "#44494a", "title_log": "#a9cfac",
    # jasne tło pod logo firmy w ciemnym motywie
    "logo_bg": "#f6f8f6", "logo_pad": "0px 6px",
}


def palette_for(widget):
    """Wybierz paletę LIGHT lub DARK według jasności tła widżetu."""
    try:
        lightness = widget.palette().window().color().lightness()
    except Exception:  # noqa: BLE001
        lightness = 255
    return DARK if lightness < 128 else LIGHT


def _section_rules(p):
    rules = []
    for v in ("cmd", "res", "log"):
        rules.append((
            "\n"
            'QFrame#section[variant="{v}"] {{ background: {card}; border: 1px '
            "solid {edge}; border-radius: 8px; }}\n"
            'QFrame#sectionHeader[variant="{v}"] {{ background: {head}; '
            "border: none;\n"
            "    border-top-left-radius: 7px; border-top-right-radius: 7px; "
            "}}\n"
            'QFrame#sectionHeader[variant="{v}"][collapsed="true"] {{\n'
            "    border-bottom-left-radius: 7px; border-bottom-right-radius: "
            "7px; }}\n"
            'QLabel#sectionTitle[variant="{v}"] {{ color: {title}; font-size: '
            "12px; font-weight: 600; background: transparent; }}\n"
            'QFrame#sectionHeader[variant="{v}"] QToolButton#linkButton {{ '
            "color: {title}; }}\n"
        ).format(v=v, card=p["card"], edge=p["edge_" + v],
                 head=p["head_" + v], title=p["title_" + v]))
    return "".join(rules)


def stylesheet(p):
    """Zwróć arkusz stylów Qt panelu i okien wtyczki dla palety p."""
    return (
        "\n"
        "QWidget#gisAssistantAIRoot {{ background: {bg}; }}\n"
        "QWidget#gisAssistantAIRoot QLabel {{ color: {text}; }}\n"
        "QScrollArea#panelScroll, QWidget#panelBody {{ background: {bg}; "
        "border: none; }}\n"
        "QFrame#header {{ background: {panel}; border: none; border-bottom: "
        "2px solid {primary}; }}\n"
        "QLabel#title {{ color: {heading}; font-size: 15px; font-weight: 600; "
        "}}\n"
        "QLabel#subtitle {{ color: {muted}; font-size: 11px; }}\n"
        "QLabel#status {{ color: {muted}; font-size: 11px; }}\n"
        "QLabel#hint {{ color: {muted}; font-size: 10px; }}\n"
        "QWidget#sectionBody {{ background: transparent; }}\n"
        "QToolButton#chevron {{ border: none; background: transparent; "
        "padding: 0px; }}\n"
        "QPlainTextEdit#prompt {{\n"
        "    border: 1px solid {border_strong}; border-radius: 6px; padding: "
        "6px 8px;\n"
        "    background: {input}; color: {text}; font-size: 12px;\n"
        "    selection-background-color: {primary}; selection-color: "
        "{on_primary};\n"
        "}}\n"
        "QPlainTextEdit#prompt:focus {{ border: 1px solid {primary}; }}\n"
        "QPushButton#primary, QPushButton#execute {{\n"
        "    background: {primary}; color: {on_primary}; border: none; "
        "border-radius: 5px;\n"
        "    padding: 6px 16px; font-weight: 600; font-size: 12px;\n"
        "}}\n"
        "QPushButton#primary:hover, QPushButton#execute:hover {{ background: "
        "{primary_hover}; }}\n"
        "QPushButton#primary:pressed, QPushButton#execute:pressed {{ "
        "background: {primary_pressed}; }}\n"
        "QPushButton#primary:disabled, QPushButton#execute:disabled {{ "
        "background: {disabled_bg}; color: {disabled_text}; }}\n"
        "QPushButton#execute {{ padding: 9px 16px; font-size: 13px; "
        "letter-spacing: 2px; }}\n"
        "QPushButton#secondary {{\n"
        "    background: transparent; color: {text}; border: 1px solid "
        "{border_strong};\n"
        "    border-radius: 5px; padding: 5px 12px; font-size: 11px;\n"
        "}}\n"
        "QPushButton#secondary:hover {{ border-color: {primary}; color: "
        "{primary_text}; }}\n"
        "QPushButton#secondary:disabled {{ color: {muted}; border-color: "
        "{border}; }}\n"
        "QPushButton#danger {{\n"
        "    background: transparent; color: {error}; border: 1px solid "
        "{error_border};\n"
        "    border-radius: 5px; padding: 5px 12px; font-size: 11px;\n"
        "}}\n"
        "QPushButton#danger:hover {{ background: {error_bg}; }}\n"
        "QPushButton#danger:disabled {{ color: {muted}; border-color: "
        "{border}; }}\n"
        "QToolButton#examples {{\n"
        "    background: {card}; color: {primary_text}; border: 1px solid "
        "{accent}; border-radius: 12px;\n"
        "    padding: 3px 10px 3px 8px; font-size: 11px; font-weight: 600;\n"
        "}}\n"
        "QToolButton#examples:hover, QToolButton#examples:pressed {{ "
        "background: {accent}; color: {on_primary}; }}\n"
        "QToolButton#examples::menu-indicator {{ image: none; width: 0px; }}\n"
        "QToolButton#iconButton {{ border: none; border-radius: 6px; padding: "
        "4px; background: transparent; }}\n"
        "QToolButton#iconButton:hover {{ background: {primary_soft}; }}\n"
        "QToolButton#linkButton {{ border: none; color: {primary_text}; "
        "background: transparent; padding: 0px 2px;\n"
        "    font-size: 11px; }}\n"
        "QToolButton#linkButton:hover {{ text-decoration: underline; }}\n"
        "QToolButton#linkButton:checked {{ font-weight: 600; }}\n"
        "QTextBrowser#result {{ border: none; background: {card}; color: "
        "{text}; }}\n"
        "QFrame#userPanel {{ background: {warn_bg}; border: 1px solid "
        "{warn_border}; border-left: 4px solid {warn};\n"
        "    border-radius: 6px; }}\n"
        "QFrame#errorPanel {{ background: {error_bg}; border: 1px solid "
        "{error_border}; border-left: 4px solid {error};\n"
        "    border-radius: 6px; }}\n"
        "QLabel#panelTitle {{ font-weight: 600; font-size: 12px; }}\n"
        "QProgressBar#busy {{ border: none; background: transparent; }}\n"
        "QProgressBar#busy::chunk {{ background: {accent}; border-radius: "
        "1px; }}\n"
        "QPlainTextEdit#log {{ background: {panel}; color: {muted}; border: "
        "none;\n"
        "    font-family: Consolas, 'DejaVu Sans Mono', monospace; font-size: "
        "10px; }}\n"
        "QFrame#footer {{ background: {panel}; border-top: 1px solid "
        "{border}; }}\n"
        "QLabel#footerLink {{ font-size: 10px; font-weight: normal; }}\n"
        "QToolButton#footerLogo {{ border: none; background: {logo_bg}; "
        "border-radius: 4px; padding: {logo_pad}; margin: 0px; }}\n"
    ).format(**p) + _section_rules(p)
