# -*- coding: utf-8 -*-
"""Разделить большой markdown-документ на части ≤ лимита (правило 10-03).

    python tools/split_doc.py <файл.md> [--limit 6000] [--apply]

Без --apply — только план (части и размеры). С --apply:
  * рядом создаётся каталог <имя без .md>/ с частями NN_<заголовок>.md и
    00_оглавление.md (список частей);
  * проверяется, что склейка частей в порядке равна исходному файлу побайтно
    (иначе ничего не удаляется и скрипт падает);
  * исходный файл удаляется (`git rm`, если файл под git).

Деление механическое, текст не переписывается: границы — заголовки `## `,
затем `### `, затем пустые строки вне блоков кода. Ссылки на исходный файл из
других документов исправляются отдельно (`--fix-links <корень>`).
"""
import io
import os
import re
import subprocess
import sys


def read_bytes(p):
    return open(p, "rb").read()


def blocks(text, pattern):
    """Разрезать по строкам, начинающимся с pattern, вне блоков кода. Склейка = text."""
    out, cur, fence = [], [], False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and re.match(pattern, line) and cur:
            out.append("".join(cur))
            cur = []
        cur.append(line)
    if cur:
        out.append("".join(cur))
    return out


def paragraphs(text):
    out, cur, fence = [], [], False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fence = not fence
        cur.append(line)
        if not fence and line.strip() == "":
            out.append("".join(cur))
            cur = []
    if cur:
        out.append("".join(cur))
    return out


def size(s):
    return len(s.encode("utf-8"))


def pieces(text, limit):
    """Список кусков ≤ limit (насколько позволяют границы), склейка = text."""
    result = []
    for level_pattern in (r"## ", r"### ", None):
        pass
    top = blocks(text, r"## ")
    for b in top:
        if size(b) <= limit:
            result.append(b)
            continue
        sub = blocks(b, r"### ")
        for s in sub:
            if size(s) <= limit:
                result.append(s)
                continue
            acc = ""
            for para in paragraphs(s):
                if acc and size(acc) + size(para) > limit:
                    result.append(acc)
                    acc = ""
                acc += para
            if acc:
                result.append(acc)
    return result


def merge(parts, limit):
    out, cur = [], ""
    for p in parts:
        if cur and size(cur) + size(p) > limit:
            out.append(cur)
            cur = ""
        cur += p
    if cur:
        out.append(cur)
    return out


def slug(text):
    m = re.search(r"^#{1,6}\s+(.+)$", text, re.M)
    if m:
        s = m.group(1).strip()
    else:
        s = next((l.strip() for l in text.splitlines() if l.strip()), "часть")
    s = re.sub(r"^\d+[а-яa-z]?\.?\s*", "", s)
    s = re.sub(r"[`*_\[\]()«»\"'.,:;!?/\\|<>—-]", " ", s).strip()
    s = re.sub(r"\s+", "_", s)
    return s[:40].strip("_") or "часть"


def title_of(text):
    m = re.search(r"^#{1,6}\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else "(без заголовка)"


def split_file(path, limit, apply):
    raw = read_bytes(path)
    text = raw.decode("utf-8")
    if size(text) <= limit:
        print("%s: %d Б ≤ %d — делить не нужно" % (path, size(text), limit))
        return None
    parts = merge(pieces(text, limit), limit)
    base = os.path.splitext(path)[0]
    names = ["%02d_%s.md" % (i, slug(p)) for i, p in enumerate(parts, 1)]
    print("%s: %d Б → %d частей" % (path, size(text), len(parts)))
    for n, p in zip(names, parts):
        print("   %-60s %5d Б%s" % (n, size(p), "  (> лимита)" if size(p) > limit else ""))
    if not apply:
        return base
    assert "".join(parts).encode("utf-8") == raw, "склейка не равна исходнику"
    os.makedirs(base, exist_ok=True)
    for n, p in zip(names, parts):
        io.open(os.path.join(base, n), "w", encoding="utf-8", newline="").write(p)
    toc = ["# %s — оглавление" % title_of(text), "",
           "Документ разделён по размеру (правило 10-03); части идут подряд.", ""]
    toc += ["* [%s](%s) — %s" % (n, n, title_of(p)) for n, p in zip(names, parts)]
    io.open(os.path.join(base, "00_оглавление.md"), "w", encoding="utf-8", newline="\n").write("\n".join(toc) + "\n")
    # проверка по файлам на диске
    back = b"".join(read_bytes(os.path.join(base, n)) for n in names)
    assert back == raw, "склейка с диска не равна исходнику"
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", path], capture_output=True,
                             cwd=os.path.dirname(os.path.abspath(path))).returncode == 0
    if tracked:
        subprocess.run(["git", "rm", "-q", "-f", os.path.basename(path)], cwd=os.path.dirname(os.path.abspath(path)), check=True)
    else:
        os.remove(path)
    print("   склейка совпадает побайтно; исходник удалён")
    return base


def repair_links(root):
    """Починить относительные ссылки на разделённые документы: x.md -> x/00_оглавление.md."""
    tocs = {}
    for dp, _d, fs in os.walk(root):
        if "00_оглавление.md" in fs:
            tocs[os.path.basename(dp)] = os.path.join(dp, "00_оглавление.md")
    fixed = [0]
    for dp, _d, fs in os.walk(root):
        for fn in fs:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            t = io.open(p, encoding="utf-8").read()

            def sub(m):
                link = m.group(1)
                if link.startswith("http") or os.path.exists(os.path.normpath(os.path.join(dp, link))):
                    return m.group(0)
                for up in ("../", "../../"):
                    if os.path.exists(os.path.normpath(os.path.join(dp, up + link))):
                        fixed[0] += 1
                        return "](%s)" % (up + link)
                stem = os.path.splitext(os.path.basename(link))[0]
                if stem in tocs:
                    fixed[0] += 1
                    return "](%s)" % os.path.relpath(tocs[stem], dp).replace("\\", "/")
                return m.group(0)
            new = re.sub(r"\]\(([^)#]+\.md)(#[^)]*)?\)", sub, t)
            if new != t:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
    return fixed[0]


def fix_links(root, old_name, new_rel_toc):
    """Заменить ссылки на old_name.md в markdown-файлах каталога root на <old>/00_оглавление.md."""
    n = 0
    for dp, _d, fs in os.walk(root):
        for fn in fs:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            t = io.open(p, encoding="utf-8").read()
            new = re.sub(r"\]\((\.?\.?/?)?%s\.md(#[^)]*)?\)" % re.escape(old_name),
                         lambda m: "](%s%s/00_оглавление.md)" % (m.group(1) or "", old_name), t)
            if new != t:
                io.open(p, "w", encoding="utf-8", newline="").write(new)
                n += 1
    return n


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    lim = 6000
    if "--limit" in a:
        lim = int(a[a.index("--limit") + 1])
    if a[0] == "--repair-links":
        print("исправлено ссылок: %d" % repair_links(a[1]))
        sys.exit(0)
    r = split_file(a[0], lim, "--apply" in a)
    if "--fix-links" in a and r and "--apply" in a:
        root = a[a.index("--fix-links") + 1]
        print("исправлены ссылки в %d файлах" % fix_links(root, os.path.splitext(os.path.basename(a[0]))[0], None))
