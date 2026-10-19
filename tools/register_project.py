# -*- coding: utf-8 -*-
"""Занести результат сверки проекта в обезличенный реестр knowledge/50_ПРОЕКТЫ/.

    python tools/register_project.py P-02

Метка → путь берётся из local/projects.txt (строки «P-nn = путь (описание)»;
файл локальный, не под git). Скрипт запускает check_project.py, затем в записи
50-NN_P-nn.md дописывает строку в раздел «История сверок» и обновляет счётчики в
`title`. Новая запись создаётся с пустыми полями «Стек» и «Записи из проекта» —
их заполняет человек или агент. Названий и путей в запись не попадает.
"""
import datetime
import glob
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "local", "projects.txt")
DIR = os.path.join(ROOT, "knowledge", "50_ПРОЕКТЫ")


def project_path(label):
    for line in io.open(REG, encoding="utf-8").read().splitlines():
        m = re.match(r"^(P-\d+)\s*=\s*(.+?)(\s+\(.*\))?$", line.strip())
        if m and m.group(1) == label:
            return m.group(2).strip()
    raise SystemExit("метка %s не найдена в local/projects.txt" % label)


def main(label):
    path = project_path(label)
    out = subprocess.run([sys.executable, "-X", "utf8", os.path.join(ROOT, "tools", "check_project.py"), path, "--summary"],
                         capture_output=True).stdout.decode("utf-8", "replace").strip()
    m = re.match(r"(\d+) ошибок, (\d+) предупреждений, в норме (\d+)", out)
    if not m:
        raise SystemExit("не удалось разобрать итог: %r" % out)
    e, w, ok = m.groups()
    today = datetime.date.today().isoformat()
    files = glob.glob(os.path.join(DIR, "50-*_%s.md" % label))
    if files:
        p = files[0]
        t = io.open(p, encoding="utf-8").read()
    else:
        nn = len(glob.glob(os.path.join(DIR, "50-*.md"))) + 1
        p = os.path.join(DIR, "50-%02d_%s.md" % (nn, label))
        t = ("---\nid: 50-%02d\ntitle: %s — проект; сверка %s\ntags: [проект, %s, сверка]\nstatus: действует\n"
             "verified: %s — отчёт tools/check_project.py\nsource: отчёт check_project.py\n---\n\n# %s\n\n"
             "* **Стек:** <заполнить, без названий>\n\n## Записи, взятые из проекта\n\n<id записей>\n\n## История сверок\n\n"
             % (nn, label, today, label, today, label))
    t = re.sub(r"^title: .*$", "title: %s — сверка %s: %s ошибок, %s предупреждений" % (label, today, e, w), t, count=1, flags=re.M)
    t = re.sub(r"^verified: .*$", "verified: %s — отчёт tools/check_project.py" % today, t, count=1, flags=re.M)
    line = "* %s: %s ошибок, %s предупреждений, в норме %s" % (today, e, w, ok)
    if "## История сверок" not in t:
        t = t.rstrip("\n") + "\n\n## История сверок\n\n"
    t = t.rstrip("\n") + "\n" + line + "\n"
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("%s: %s" % (os.path.basename(p), line))


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
