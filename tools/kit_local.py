# -*- coding: utf-8 -*-
"""Особое для набора context в общей проверке skill-skill/tools/check_docs.py.

extra_checks(root): у каждой записи базы есть строка в tools/when.txt — иначе
make_index.py оставит в колонке «Когда» прочерк (00, «Добавление записи»).
"""
import io
import os
import re


def extra_checks(root):
    kn = os.path.join(root, "knowledge")
    when_path = os.path.join(root, "tools", "when.txt")
    when = set()
    if os.path.exists(when_path):
        for line in io.open(when_path, encoding="utf-8").read().splitlines():
            if "\t" in line:
                when.add(line.split("\t", 1)[0].strip())
    out = []
    for dp, _dn, fn in os.walk(kn):
        for f in sorted(fn):
            if not f.endswith(".md") or f in ("INDEX.md", "00_ПРАВИЛА.md"):
                continue
            head = io.open(os.path.join(dp, f), encoding="utf-8").read(400)
            m = re.search(r"^id:\s*\"?([\w-]+)", head, re.M)
            if m and m.group(1) not in when:
                out.append("%s: нет строки в tools/when.txt — колонка «Когда» "
                           "в INDEX.md останется пустой" % m.group(1))
    return out
