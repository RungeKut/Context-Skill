# -*- coding: utf-8 -*-
"""Проверка текста коммита набора на упоминание рабочего проекта.

check_docs.py сверяет файлы набора, а сообщение коммита не видит ни один из
них. Запускается хуком tools/hooks/commit-msg (его включает setup.ps1):

    python tools/check_msg.py .git/COMMIT_EDITMSG

Стоп-слова — tools/stoplist.txt (локальный). Папку проекта можно добавить:

    git config contextkit.project "D:/путь/к/папке/проекта"
"""
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from check_docs import project_words, stop_words   # noqa: E402


def git_config(name):
    try:
        out = subprocess.check_output(["git", "config", "--get", name],
                                      cwd=ROOT, stderr=subprocess.DEVNULL)
        return out.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def main(argv):
    if not argv or not os.path.exists(argv[0]):
        print("check_msg.py: нужен путь к файлу с текстом коммита")
        return 2
    lines = [l for l in io.open(argv[0], encoding="utf-8", errors="replace")
             .read().splitlines() if not l.lstrip().startswith("#")]
    text = "\n".join(lines).lower()
    words = stop_words() | project_words(git_config("contextkit.project"))
    hits = sorted({w for w in words if w.lower() in text})
    if not hits:
        return 0
    print("\n  КОММИТ ОТКЛОНЁН: в сообщении упомянут рабочий проект")
    for w in hits:
        print("    - %r" % w)
    print("\n  Набор — знание о способе работы, а не история проектов, и репозиторий")
    print("  готовится к публикации. Перепишите без названия: «в проекте с")
    print("  прошивкой» вместо названия. Правило: knowledge/40_СРЕДА/40-02.\n")
    return 1


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
