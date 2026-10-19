# -*- coding: utf-8 -*-
"""Проверка целостности базы знаний Context-Kit.

Выполняет раздел 9 файла knowledge/00_ПРАВИЛА.md:

  * у каждого файла базы есть шапка YAML с обязательными полями;
  * каждый файл присутствует в INDEX.md и наоборот;
  * нет двух файлов с одинаковым id; id в шапке совпадает с именем файла;
  * записи со status: проверено имеют verified и applies_to;
  * внутренние ссылки ведут на существующие файлы;
  * записи базы не длиннее MAX_LINES строк (одна запись — одна тема);
  * frontmatter skill/SKILL.md разбирается, description в кавычках;
  * НИ ОДИН файл набора не упоминает рабочий проект (стоп-слова);
  * включён хук commit-msg и задан автор коммитов клона.

Стоп-слова — tools/stoplist.txt: ЛОКАЛЬНЫЙ файл (в .gitignore). Реестр
проектов — каталог local/ (тоже в .gitignore): набор публикуем, а названия
проектов, с которыми он сверялся, в публичный репозиторий не идут.

Запуск:
    python tools/check_docs.py
    python tools/check_docs.py --project "D:\\путь\\к\\папке\\проекта"
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE = os.path.join(ROOT, "knowledge")
INDEX = os.path.join(KNOWLEDGE, "INDEX.md")
SKILL = os.path.join(ROOT, "skill", "SKILL.md")
STOPLIST = os.path.join(ROOT, "tools", "stoplist.txt")

REQUIRED = ("id", "title", "status")
VALID_STATUS = ("проверено", "не проверено", "устарело", "действует")
MAX_LINES = 200
SKIP = ("tools/stoplist.txt",)
TEXT_EXT = (".md", ".py", ".ps1", ".txt", ".bat", ".json", ".yml", ".toml")
GENERIC = set("""project docs state index rules agents main build test data
проект проекта документы правила агенты состояние индекс claude code kit""".split())


def read(path):
    return io.open(path, encoding="utf-8").read()


def front_matter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    out = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def knowledge_files():
    out = []
    for dirpath, _d, filenames in os.walk(KNOWLEDGE):
        for fn in sorted(filenames):
            if fn.endswith(".md") and fn != "INDEX.md":
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def rel(path):
    return os.path.relpath(path, KNOWLEDGE).replace("\\", "/")


def git(*args):
    try:
        out = subprocess.check_output(["git", *args], cwd=ROOT,
                                      stderr=subprocess.DEVNULL)
        return out.decode("utf-8", "replace").strip()
    except Exception:
        return None


def hook_enabled():
    v = git("config", "--get", "core.hooksPath")
    return v is not None and v.replace("\\", "/") == "tools/hooks"


def local_author():
    n, e = git("config", "--local", "--get", "user.name"), \
        git("config", "--local", "--get", "user.email")
    return (n, e) if n and e else None


def tracked(path):
    return bool(git("ls-files", "--", path))


def repo_files():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", ".venv", "local")]
        for fn in sorted(filenames):
            if not fn.lower().endswith(TEXT_EXT):
                continue
            full = os.path.join(dirpath, fn)
            if os.path.relpath(full, ROOT).replace(os.sep, "/") in SKIP:
                continue
            out.append(full)
    return sorted(out)


def stop_words():
    if not os.path.exists(STOPLIST):
        return set()
    out = set()
    for line in io.open(STOPLIST, encoding="utf-8-sig").read().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def project_words(project_dir):
    """Приметы проекта: имя его папки (токены от 4 знаков)."""
    if not project_dir or not os.path.isdir(project_dir):
        return set()
    name = os.path.basename(os.path.abspath(project_dir))
    return {t for t in re.split(r"[^0-9A-Za-zА-Яа-яЁё]+", name)
            if len(t) >= 4 and t.lower() not in GENERIC}


def check_skill(problems):
    if not os.path.exists(SKILL):
        problems.append("нет skill/SKILL.md")
        return
    text = read(SKILL)
    fm = front_matter(text)
    if fm is None or "name" not in fm or "description" not in fm:
        problems.append("skill/SKILL.md: нет frontmatter с name и description")
        return
    d = fm["description"]
    if not (d.startswith('"') and d.endswith('"')) and re.search(r":\s", d):
        problems.append("skill/SKILL.md: description с «: » без кавычек — "
                        "часть загрузчиков молча не видит скилл")
    if len(d) > 1024:
        problems.append("skill/SKILL.md: description %d знаков, предел 1024"
                        % len(d))


def main(project_dir=None):
    problems, ids = [], {}
    files = knowledge_files()
    print("База знаний: %s" % KNOWLEDGE)
    print("Файлов найдено: %d\n" % len(files))

    for path in files:
        r = rel(path)
        text = read(path)
        fm = front_matter(text)
        if fm is None:
            problems.append("%s: нет шапки YAML" % r)
            continue
        for field in REQUIRED:
            if field not in fm:
                problems.append("%s: в шапке нет поля %s" % (r, field))
        status = fm.get("status", "")
        if status and status not in VALID_STATUS:
            problems.append("%s: неизвестный status %r" % (r, status))
        if status == "проверено" and not fm.get("verified"):
            problems.append("%s: «проверено» без verified — запись не имеет силы" % r)
        if status == "проверено" and not fm.get("applies_to"):
            problems.append("%s: нет applies_to" % r)
        if len(text.splitlines()) > MAX_LINES:
            problems.append("%s: больше %d строк — разделить (одна тема на файл)"
                            % (r, MAX_LINES))
        fid = fm.get("id", "")
        if fid:
            if fid in ids:
                problems.append("%s: id %s уже занят %s" % (r, fid, ids[fid]))
            else:
                ids[fid] = r
            base = os.path.basename(path)
            if not base.startswith(fid + "_") and base != "00_ПРАВИЛА.md":
                problems.append("%s: id %s не совпадает с именем файла" % (r, fid))

    if not os.path.exists(INDEX):
        problems.append("нет INDEX.md")
    else:
        index_text = read(INDEX)
        linked = {l.replace("\\", "/") for l in
                  re.findall(r"\]\(([^)]+\.md)\)", index_text)}
        for path in files:
            if rel(path) not in linked:
                problems.append("%s: файла нет в INDEX.md" % rel(path))
        existing = {rel(p) for p in files}
        for l in sorted(linked):
            if l not in existing and not l.startswith(".."):
                problems.append("INDEX.md ссылается на несуществующий %s" % l)
        width = None
        for n, line in enumerate(index_text.splitlines(), 1):
            if not line.startswith("|"):
                width = None
                continue
            cells = line.count("|")
            if width is None:
                width = cells
            elif cells != width:
                problems.append("INDEX.md, строка %d: %d ячеек вместо %d"
                                % (n, cells - 1, width - 1))

    for path in files:
        base = os.path.dirname(path)
        for link in re.findall(r"\]\(([^)]+\.md)\)", read(path)):
            if link.startswith("http"):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(base, link))):
                problems.append("%s: битая ссылка -> %s" % (rel(path), link))

    check_skill(problems)

    if not os.path.exists(STOPLIST):
        problems.append("нет tools/stoplist.txt (локальный, заводит setup.ps1)")
    if tracked("tools/stoplist.txt"):
        problems.append("tools/stoplist.txt под git — git rm --cached tools/stoplist.txt")
    if tracked("local"):
        problems.append("каталог local/ под git — реестр проектов должен быть локальным")
    project = project_words(project_dir)
    if project:
        print("Приметы проекта: %s\n" % ", ".join(sorted(project)))
    words = stop_words() | project
    for path in repo_files():
        text = read(path).lower()
        r = os.path.relpath(path, ROOT).replace(os.sep, "/")
        for word in sorted(words):
            if word.lower() in text:
                problems.append("%s: упоминание проекта %r (правило 1)" % (r, word))

    if not hook_enabled():
        problems.append("хук commit-msg не включён: git config core.hooksPath tools/hooks")
    if local_author() is None:
        problems.append("для клона не задан автор коммитов (git config user.name/user.email без --global)")

    if problems:
        print("РАСХОЖДЕНИЯ (%d):" % len(problems))
        for p in problems:
            print("  - " + p)
    else:
        print("Расхождений нет.")
    print("\nЗанятые id: %s" % ", ".join(sorted(ids)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    argv = sys.argv[1:]
    proj = None
    if "--project" in argv:
        i = argv.index("--project")
        if i + 1 >= len(argv):
            print("--project требует путь к папке проекта")
            sys.exit(2)
        proj = argv[i + 1]
    sys.exit(main(proj))
