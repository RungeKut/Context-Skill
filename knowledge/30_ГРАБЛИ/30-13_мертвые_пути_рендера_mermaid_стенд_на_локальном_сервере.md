---
id: 30-13
title: Рендер mermaid в SVG без рабочего mmdc — четыре мёртвых пути (корпоративное npm-зеркало, Edge headless, jsdom, printf-JSON) и стенд на локальном сервере с IAB-браузером; evaluate IAB — только выражения-IIFE, аргументы не доезжают, промисы не ожидаются
tags: [mermaid, svg, диаграммы, npm, puppeteer, jsdom, iab, evaluate]
applies_to: ZCode IAB-браузер, Node 24, mermaid 11 (UMD), Windows
status: проверено
verified: 2026-11-17 — практика P-04, четыре пути проверены подряд в одной сессии
source: практика P-04
---

# Мёртвые пути рендера mermaid и рабочий стенд

Нужно: превратить `.mmd` в готовый `.svg` до пуша (причина — 30-11).
Ниже — куда НЕ ходить (проверено, сожжено ~30 минут) и что работает.

## Мёртвые пути

1. `npx @mermaid-js/mermaid-cli` — 404: корпоративное npm-зеркало
   (verdaccio) не содержит пакет. Прямой `--registry=https://registry.npmjs.org`
   доступен, но mmdc тянет puppeteer с отдельного CDN — не обязательный
   обход, есть путь проще.
2. Puppeteer + системный Edge (`headless` любой) — запуск виснет
   молча («Failed to launch the browser process: Code: 0», или тишина до
   таймаута). Не чинить флагами.
3. jsdom + mermaid в Node — падает на `getBBox is not defined` и
   `CSSStyleSheet`: jsdom не умеет геометрию SVG; шимы дают фейковые
   размеры и кривую раскладку.
4. Windows-путь в JSON через bash `printf '\\\\'` — бэкслеши съедаются,
   получается невалидный JSON («Bad escaped character»). Конфиги писать
   python `json.dumps`, не printf/heredoc.

## Рабочий стенд (сохранён в наборе)

`tools/mermaid_render/`: `www/index.html` + `www/mermaid.min.js`
(UMD-сборка, 5,5 МБ, уже в наборе — не качать) + `start_server.py`
(локальный HTTP, порт 8631). Запуск: `python tools/mermaid_render/start_server.py`
из корня набора, далее встроенный браузер (IAB) открывает
`http://127.0.0.1:8631/index.html`.

Страница экспортирует `window.renderDiagram(src)` (mermaid.render,
theme default, htmlLabels) и кладёт результат в `window.__lastSvg`,
статус — `window.__status` ('OK' / 'ERR: …').

## Особенности evaluate у IAB (главная экономия токенов)

- Аргументы в `evaluate((s) => …, значение)` **не доезжают** — функция
  получает undefined, молча. Данные встраивать в код: строку исходника —
  через `JSON.stringify` на стороне Node прямо в тело вызова.
- Принимаются **выражения**, не инструкции: `Unexpected token ';'`.
  Оборачивать в `(() => { … })()`.
- Возвращённый промис **не ожидается**: вернётся `{}`. Паттерн
  «пнуть — подождать — прочитать»: evaluate(IIFE-запуск) →
  `waitForTimeout(1200–1500)` → отдельный evaluate читает
  `window.__lastSvg` (строка возвращается нормально).

## Пост-обработка SVG (по 30-11)

`<br>` → `<br/>`; белый фон `<rect width="100%" height="100%"
fill="#ffffff"/>` сразу после открывающего `<svg>`; проверка
`xml.etree` парсером. Диаграмму с кириллицей и раскладкой проверять
скриншотом вкладки один раз — рендер без ошибок не гарантирует
читаемость.

## Чем подтверждено

Практика P-04, 2026-11-17: три диаграммы отрендерены стендом за один
проход (39–22 КБ SVG), XML валиден, кириллица и фон — по скриншоту ок.
