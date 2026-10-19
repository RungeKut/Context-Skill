# -*- coding: utf-8 -*-
"""Сверка проекта с правилами Context-Kit.

    python tools/check_project.py "D:\\путь\\к\\проекту"

Проверяет (knowledge/10_ДОКУМЕНТАЦИЯ, 20_АГЕНТЫ):
  * корневой AGENTS.md / CLAUDE.md: есть, ≤ 2 КБ (ошибка > 4 КБ), содержимое
    одинаково, есть запрет комментариев;
  * docs/INDEX.md (таблица «Файл | Когда») и docs/50_status/STATE.md
    («Обновлено:», ≤ 6 КБ);
  * docs/00_rules/ с token-economy, agents, compact;
  * каждый документ docs/ ≤ 6 КБ, кроме строк INDEX с пометкой «журнал» (дописываемый)
    или «монолит» (на файл ссылаются код, тесты или релизные ссылки; причина — в INDEX);
  * каждый документ есть в INDEX, и наоборот.

Код возврата 1 — есть ОШИБКИ; предупреждения его не меняют.
Отчёт можно сохранить: ... > отчёт.txt — он и есть сверка «проект ↔ набор».
"""
import io
import os
import re
import sys

ROOT_FILE_LIMIT = 2048
ROOT_FILE_HARD = 4096
DOC_LIMIT = 6144
RULES = ("token-economy.md", "agents.md", "compact.md")


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def main(project):
    errors, warns, info = [], [], []
    if not os.path.isdir(project):
        print("нет папки %s" % project)
        return 2

    # --- корневой файл ---
    roots = [n for n in ("AGENTS.md", "CLAUDE.md") if os.path.exists(os.path.join(project, n))]
    if not roots:
        errors.append("нет корневого AGENTS.md / CLAUDE.md (его читает каждый субагент)")
    texts = {}
    for n in roots:
        size = os.path.getsize(os.path.join(project, n))
        texts[n] = read(os.path.join(project, n))
        if size > ROOT_FILE_HARD:
            errors.append("%s: %d Б — больше %d, сжать (правило 10-01)" % (n, size, ROOT_FILE_HARD))
        elif size > ROOT_FILE_LIMIT:
            warns.append("%s: %d Б — больше %d" % (n, size, ROOT_FILE_LIMIT))
        else:
            info.append("%s: %d Б — в норме" % (n, size))
        if not re.search(r"омментари", texts[n]):
            warns.append("%s: нет правила про комментарии в коде" % n)
    if len(texts) == 2 and texts["AGENTS.md"] != texts["CLAUDE.md"]:
        warns.append("AGENTS.md и CLAUDE.md различаются — канон один файл (10-01)")

    docs = os.path.join(project, "docs")
    if not os.path.isdir(docs):
        errors.append("нет каталога docs/ — документация вне структуры Context-Kit")
        return report(project, errors, warns, info)

    # --- INDEX и STATE ---
    index = os.path.join(docs, "INDEX.md")
    index_text = read(index) if os.path.exists(index) else ""
    if not index_text:
        errors.append("нет docs/INDEX.md (таблица «Файл | Когда»)")
    elif not re.search(r"\|\s*Файл\s*\|\s*Когда\s*\|", index_text):
        warns.append("docs/INDEX.md: нет таблицы «Файл | Когда»")
    state = os.path.join(docs, "50_status", "STATE.md")
    if not os.path.exists(state):
        errors.append("нет docs/50_status/STATE.md (точка возобновления)")
    else:
        st = read(state)
        size = os.path.getsize(state)
        m = re.search(r"Обновлено:\s*(\d{4}-\d{2}-\d{2})", st)
        if not m:
            warns.append("STATE.md: нет строки «Обновлено: <дата>»")
        else:
            info.append("STATE.md обновлён %s" % m.group(1))
        if size > DOC_LIMIT:
            errors.append("STATE.md: %d Б — стал летописью; оставить текущее, остальное в архив (30-02)" % size)
        for sec in ("Следующий шаг", "Открытые вопросы"):
            if sec not in st:
                warns.append("STATE.md: нет раздела «%s»" % sec)

    # --- правила процесса ---
    for r in RULES:
        if not os.path.exists(os.path.join(docs, "00_rules", r)):
            warns.append("нет docs/00_rules/%s" % r)

    # --- размеры и индекс ---
    journal = set()
    linked = set()
    for line in index_text.splitlines():
        for l in re.findall(r"`([^`]+(?:\.md|/))`|\]\(([^)]+\.md)\)", line):
            path = (l[0] or l[1]).replace("\\", "/")
            linked.add(path)
            if "журнал" in line.lower() or "монолит" in line.lower():
                journal.add(path)
    for dirpath, _d, files in os.walk(docs):
        for fn in files:
            if not fn.endswith(".md") or fn == "INDEX.md":
                continue
            full = os.path.join(dirpath, fn)
            r = os.path.relpath(full, docs).replace("\\", "/")
            size = os.path.getsize(full)
            in_journal = r in journal or any(j.endswith("/") and r.startswith(j) for j in journal)
            if size > DOC_LIMIT and not in_journal:
                warns.append("docs/%s: %d Б > %d — разделить (tools/split_doc.py) или пометить «журнал»/«монолит» в INDEX (10-03)" % (r, size, DOC_LIMIT))
            if r not in linked and not any(l.endswith(r) or (l.endswith("/") and r.startswith(l)) for l in linked):
                warns.append("docs/%s: нет в INDEX.md" % r)
    return report(project, errors, warns, info)


SUMMARY = False


def report(project, errors, warns, info):
    if SUMMARY:
        print("%d ошибок, %d предупреждений, в норме %d" % (len(errors), len(warns), len(info)))
        return 1 if errors else 0
    print("Проект: %s\n" % project)
    for title, items in (("ОШИБКИ", errors), ("ПРЕДУПРЕЖДЕНИЯ", warns), ("В НОРМЕ", info)):
        print("%s (%d)" % (title, len(items)))
        for i in items:
            print("  - " + i)
        print()
    return 1 if errors else 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if a != "--summary"]
    SUMMARY = "--summary" in sys.argv[1:]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0]))
