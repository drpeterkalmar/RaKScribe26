"""Befund in die Windows-Zwischenablage (Gutachten 05.10. P1-1) — ohne Windows importierbar und testbar.

Windows-OpenClipboard schlägt fehl, solange ein anderes Programm (RIS, Teams, Zwischenablage-Manager) die
Zwischenablage hält. Früher wurde der Fehler verschluckt und trotzdem Strg+V gedrückt → der VORIGE Befund landete
im RIS. Jetzt: mehrere Versuche, Gegenlesen, und der Aufrufer fügt nur bei True ein.

win32clipboard und markdown werden erst in clipboard_set() geladen (oder vom Aufrufer übergeben), damit das Modul
auf dem Mac mit einem Mock getestet werden kann (tests/offline/test_clipboard.py).
"""
import time

VERSUCHE = 5
PAUSE_S = 0.1

_HTML_HEADER = ("Version:1.0\r\nStartHTML:{0:08d}\r\nEndHTML:{1:08d}\r\n"
                "StartFragment:{2:08d}\r\nEndFragment:{3:08d}\r\nSourceURL:none\r\n")


def html_format_bytes(md_text, md_to_html):
    """Clipboard-Format "HTML Format" (CF_HTML) für Word/RIS: Header mit Offsets + HTML-Dokument (UTF-8).
    Offsets wie seit v2.x berechnet (Zeichen, nicht Bytes — siehe Umbau-Bericht, offener Punkt)."""
    html = md_to_html(md_text)
    frag = f"<html><head><meta charset='utf-8'></head><body>{html}</body></html>"
    s_html = len(_HTML_HEADER.format(0, 0, 0, 0))
    s_frag = s_html + frag.find("<body>") + 6
    e_frag = s_html + frag.find("</body>")
    e_html = s_html + len(frag)
    return (_HTML_HEADER.format(s_html, e_html, s_frag, e_frag) + frag).encode('utf-8')


def zwischenablage_setzen(cb, html_format_bytes_, text, versuche=VERSUCHE, pause=PAUSE_S, sleep=time.sleep):
    """Setzt HTML + Unicode-Text in die Windows-Zwischenablage. cb = win32clipboard-Modul (oder Mock).
    Gibt True nur zurück, wenn der Text danach nachweislich drinsteht."""
    for i in range(versuche):
        offen = False
        try:
            cb.OpenClipboard()
            offen = True
            cb.EmptyClipboard()
            if html_format_bytes_ is not None:
                cb.SetClipboardData(cb.RegisterClipboardFormat("HTML Format"), html_format_bytes_)
            cb.SetClipboardData(cb.CF_UNICODETEXT, text)
            cb.CloseClipboard()
            offen = False
            # Gegenlesen: steht wirklich unser Text drin?
            cb.OpenClipboard()
            offen = True
            gelesen = cb.GetClipboardData(cb.CF_UNICODETEXT)
            cb.CloseClipboard()
            offen = False
            if (gelesen or "").replace("\r\n", "\n").strip() == text.replace("\r\n", "\n").strip():
                return True
        except Exception:
            pass
        finally:
            if offen:
                try:
                    cb.CloseClipboard()
                except Exception:
                    pass
        if i < versuche - 1:
            sleep(pause)
    return False


def clipboard_set(md_text, cb=None, md_to_html=None, sleep=time.sleep, log=None):
    """Befund (Markdown-Text + HTML für Word) in die Zwischenablage. True nur bei nachweislichem Erfolg."""
    if not md_text:
        return False
    if cb is None:
        import win32clipboard as cb
    try:
        if md_to_html is None:
            import markdown
            md_to_html = markdown.markdown
        html = html_format_bytes(md_text, md_to_html)
    except Exception as e:
        if log:
            log(f"[COPY] HTML-Aufbereitung fehlgeschlagen — kopiere nur Text ({e})")
        html = None
    return zwischenablage_setzen(cb, html, md_text, sleep=sleep)
