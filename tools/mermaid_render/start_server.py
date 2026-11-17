#!/usr/bin/env python3
"""Локальный стенд рендера mermaid -> SVG (грабли 30-13).

Поднимает HTTP-сервер (127.0.0.1:8631) на папке www/ и держит её,
пока не остановят (Ctrl+C). Далее встроенный браузер (IAB) открывает
http://127.0.0.1:8631/index.html и вызывает window.renderDiagram(src).

Паттерн работы с IAB (evaluate IAB принимает только выражения-IIFE,
аргументы не доезжают, промисы не ожидаются):

  evaluate: (() => { window.renderDiagram(<JSON.stringify(src>); })()
  waitForTimeout(1200..1500)
  evaluate: window.__lastSvg   -> сохранить в .svg

Пост-обработка SVG — по 30-11: <br> -> <br/>, белый rect, проверка XML.
"""
import http.server
import os
import sys

PORT = 8631
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")


def main() -> int:
    if not os.path.isfile(os.path.join(ROOT, "mermaid.min.js")):
        print("нет www/mermaid.min.js — см. 30-13", file=sys.stderr)
        return 1
    os.chdir(ROOT)
    print("mermaid render stand: http://127.0.0.1:%d/index.html" % PORT)
    print("Ctrl+C — остановить", flush=True)
    http.server.ThreadingHTTPServer(
        ("127.0.0.1", PORT), http.server.SimpleHTTPRequestHandler
    ).serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
