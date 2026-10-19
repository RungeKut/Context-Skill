# -*- coding: utf-8 -*-
"""Пересобрать knowledge/INDEX.md из шапок записей (id, title, status).

Колонка «Когда» берётся из tools/when.txt (строки «id<TAB>когда читать»);
запись без строки получает «—» и check_docs.py её не пропустит как заполненную
ошибка — поэтому при добавлении записи добавляйте строку в when.txt.
Раздел «По симптому» ведётся вручную в tools/symptoms.md и дописывается как есть.

    python tools/make_index.py
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K = os.path.join(ROOT, "knowledge")
SECTIONS = [
    ("10", "10_ДОКУМЕНТЫ — как устроены документы проекта"),
    ("20", "20_ПРИЁМЫ — как работать с агентами и токенами"),
    ("30", "30_ГРАБЛИ — что ломается"),
    ("40", "40_СРЕДА — установка и репозиторий"),
    ("50", "50_ПРОЕКТЫ — реестр подключённых проектов"),
]


def read(p):
    return io.open(p, encoding="utf-8").read()


def main():
    when = {}
    wp = os.path.join(ROOT, "tools", "when.txt")
    if os.path.exists(wp):
        for line in read(wp).splitlines():
            if "\t" in line:
                k, v = line.split("\t", 1)
                when[k.strip()] = v.strip()
    rows = []
    for dp, _d, fs in sorted(os.walk(K)):
        for fn in sorted(fs):
            if not fn.endswith(".md") or fn in ("INDEX.md", "00_ПРАВИЛА.md"):
                continue
            t = read(os.path.join(dp, fn))
            fm = dict(re.findall(r"^(\w+):\s*(.*)$", t.split("\n---")[0], re.M))
            rel = os.path.relpath(os.path.join(dp, fn), K).replace("\\", "/")
            rows.append((fm["id"], rel, fm["title"].strip('"'), fm.get("status", "")))
    out = ["# INDEX базы знаний Context-Kit", "",
           "Открывай запись, только если задача попала в колонку «Когда». "
           "Закон базы — [00_ПРАВИЛА.md](00_ПРАВИЛА.md).", ""]
    for k, name in SECTIONS:
        out += ["## " + name, "", "| id | Утверждение | Когда | Статус |", "|---|---|---|---|"]
        for rid, rel, title, st in rows:
            if rid.startswith(k):
                out.append("| [%s](%s) | %s | %s | %s |" % (rid, rel, title.replace("|", "/"), when.get(rid, "—"), st))
        out.append("")
    sp = os.path.join(ROOT, "tools", "symptoms.md")
    if os.path.exists(sp):
        out.append(read(sp).rstrip("\n"))
        out.append("")
    io.open(os.path.join(K, "INDEX.md"), "w", encoding="utf-8", newline="\n").write("\n".join(out))
    print("INDEX.md: %d записей" % len(rows))


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
