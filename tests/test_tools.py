# -*- coding: utf-8 -*-
"""Проверки инструментов набора без внешних зависимостей.

    python tests/test_tools.py
"""
import io
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def run(*args):
    p = subprocess.run([PY, *args], capture_output=True, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def good_project(d):
    write(os.path.join(d, "AGENTS.md"), "# P\nКомментарии в коде запрещены.\n")
    write(os.path.join(d, "CLAUDE.md"), "# P\nКомментарии в коде запрещены.\n")
    write(os.path.join(d, "docs", "INDEX.md"),
          "| Файл | Когда |\n|---|---|\n| `50_status/STATE.md` | старт |\n")
    write(os.path.join(d, "docs", "50_status", "STATE.md"),
          "# Состояние\nОбновлено: 2026-10-19\n## Следующий шаг\n- x\n## Открытые вопросы\n- y\n")
    for r in ("token-economy", "agents", "compact"):
        write(os.path.join(d, "docs", "00_rules", r + ".md"), "# " + r + "\n")


def main():
    ok = []

    def check(name, cond):
        print(("OK   " if cond else "FAIL ") + name)
        ok.append(bool(cond))

    rc, out = run(os.path.join(ROOT, "tools", "check_docs.py"))
    check("check_docs: база целостна", rc == 0 and "Расхождений нет" in out)

    with tempfile.TemporaryDirectory() as d:
        rc, out = run(os.path.join(ROOT, "tools", "check_project.py"), d)
        check("check_project: пустая папка — ошибки", rc == 1 and "нет корневого" in out)
        good_project(d)
        rc, out = run(os.path.join(ROOT, "tools", "check_project.py"), d)
        check("check_project: правильный проект — без ошибок", rc == 0 and "ОШИБКИ (0)" in out)
        write(os.path.join(d, "AGENTS.md"), "x" * 5000)
        rc, out = run(os.path.join(ROOT, "tools", "check_project.py"), d)
        check("check_project: корневой файл 5 КБ — ошибка", rc == 1 and "AGENTS.md" in out)
        good_project(d)
        write(os.path.join(d, "docs", "10_big", "big.md"), "z" * 7000)
        rc, out = run(os.path.join(ROOT, "tools", "check_project.py"), d)
        check("check_project: документ > 6 КБ — предупреждение", "big.md" in out and "ПРЕДУПРЕЖДЕНИЯ" in out)

    print("\nИТОГ:", "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" if all(ok) else "ЕСТЬ ПРОВАЛЫ")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
