# 🔑 Open AG Patcher — модификация 1.3.9

Форк официального `open-antigravity-patcher` **1.3.8**.
Гейты сверены с `agy` 1.4.0 (x64 Linux).

## Атрибуция

- Оригинал: [AvenCores/open-antigravity-patcher](https://github.com/AvenCores/open-antigravity-patcher) (GPL-3.0),
  зеркала: [SourceForge](https://sourceforge.net/projects/open-antigravity-patcher/),
  [GitLab](https://gitlab.com/avencores/open-antigravity-patcher).
  База мода — официальный релиз **1.3.8** (включая его ARM64-гейты W2/W4,
  атомарную запись и макосные фиксы).
  Автор оригинала — **AvenCores**. Часть решений оригинала основана на
  [QNIX-Dev/eligibility-antigravity-patcher](https://github.com/QNIX-Dev/eligibility-antigravity-patcher) (MIT).
- Настоящая модификация 1.3.9 — сторонний форк: добавлены гейты 2–3 для `agy`,
  пофикшены поиск бинарей, `sudo`-флоу и бэкапы (список ниже).
  Распространяется под той же лицензией GPL-3.0 (`LICENSE`).

## Что не так в оригинале 1.3.8

Оригинальный `patcher/agy/patcher.py` содержит **только 1 гейт**:

- Gate 1 (`CLI_GATE`): `test rax,rax; je; cmp byte[rax+8],0; jne` @ `0x8bcb580`
  (`48 85 C0 90` вместо `80 78 08 00`).

Проверено на `agy` 1.4.0 (220 МБ, Go 1.28):

- `agy models` — работает даже с Gate 1.
- `agy -p "hi"` — **падает и с Gate 1**:
  - pristine: `error: Eligibility check failed: Your current account is not eligible for Antigravity, because it is not currently available in your location.`
  - Gate-1-patched: `error: Eligibility check failed: ` (пусто).
- Лог `~/.gemini/antigravity-cli/log/cli-*.log`:
  - `server_oauth.go:134] Account ineligible: `
  - `printmode.go:291] Print mode: eligibility check failed: Eligibility check failed: `

Причина: решение принимается **по `[rcx+8]` до вызова Gate 1** (`0x8bfda20`),
поэтому патч `rax`-гейта на этот путь не влияет (неправильный регистр).
Плюс внутри `agy` скомпилирован тот же `hasValidAuth`-чек, что в `language_server`,
но `manager`-патчер его не трогает (только `language_server`-бинарь).

## Что добавлено в 1.3.9

Все гейты — в `source/patcher/agy/patcher.py`, `ALL_GATES` (3 шт.):

1. `eligibility screen off` (официальный гейт 1.3.8 без изменений:
   x64 + arm64 + arm64 w2/w4 для CLI 1.2.7+).
2. `hasValidAuth=true inside agy` (**НОВЫЙ**, портирован из `manager/patcher.py`).
   - Найден в `agy` @ `0x848df8a` (1 вхождение, unpatched даже при патченном Gate 1):
     `80 78 08 00 74.. 48 8B.. 24.. 48 89.. 60` → `C6 40 08 01 90 90`.
   - arm64-ветка — та же, что в менеджере.
3. `print-mode eligibility (rcx) off` (**НОВЫЙ**, чинит `agy -p`, x64).
   - Уникальный (1 вхождение) @ `0x8bfda20`:
     `48 85 C0 0F 85.... 48 85 C9 0F 84.... 80 79 08 00 0F 85....`
     → `48 85 C9 90`, `offset=18`.
   - Смысл: `cmp byte[rcx+8],0` → `test rcx,rcx+nop`; `rcx` здесь non-nil,
     поэтому `jne ok` всегда берётся.
   - `80 79` = `cmp [rcx+8]`, в отличие от `80 78` = `cmp [rax+8]` в Gate 1.
   - arm64-варианта нет (нет arm64-бинаря для сверки) — на arm64 честный
     `LookupError`, а не неверный патч.

Дополнительно починено при прогоне всего патчера:

- `patcher/agy/discovery.py::_posix_find` — явные фолбэки
  (`~/.local/bin/agy`, `~/bin/agy`, `/usr/local/bin/agy`, `/opt/...`,
  дом sudo-пользователя). Лечит `"Antigravity CLI path is not set"`
  при запуске с аргументом, под sudo без PATH или из symlink.
- `patcher/cli.py::run_cli` — автопоиск по каждой цели отдельно.
  Раньше поиск срабатывал только когда ВСЕ пути пусты: запуск
  `main.py <ide-path>` навсегда оставлял `agy_path=""` и пункт 3
  упирался в `offer_download_and_block`. Плюс повторный
  `find_agy_binary()`/`find_manager_binary()` прямо перед пунктами 2/3.
- `patcher/manager/discovery.py::resolve_manager_path` — строгий:
  чужой файл (напр. `agy`) больше не считается `language_server`.
  Плюс поиск `language_server*` в `~/.local/opt`.
- `source/main.py` — sudo спрашивается только для системных путей.
  Юзерская установка идёт сразу (`[+] User-local install detected`).
- `patcher/agy/patcher.py::_make_backup` — существующий бэкап молча
  не перезаписываем (апгрейд не уничтожает pristine-оригинал).

## Сверка гейтов

```bash
# Gate 1: 1 вхождение в pristine, 1 patched в патченном
# 0x8bcb580: sig=1/patched=0 (pristine .agybak), sig=0/patched=1 (патченный agy)

# Gate 2 (manager-паттерн внутри agy): 1 вхождение
# 0x848df8a: 80 78 08 00 74 3B 48 8B 54 24 70 48 89 50 60

# Gate 3 (rcx): уникален
# 0x8bfda20: 48 85 C0 0F 85.... 48 85 C9 0F 84.... 80 79 08 00 0F 85....
```

Метод: `objdump -d --start-address ...`, `strings -a`,
xref `lea [rip+...]` сканером (`48-4F 8D 05/0D/...`).

## Проверка

```bash
cp ~/.local/bin/agy.agybak /tmp/agy_test
PYTHONPATH=source python3 -c "from patcher.agy.patcher import get_status; print(get_status('/tmp/agy_test'))"
# до: ('unpatched', None), после патча: ('patched', None)
```

Протестировано на `agy` 1.4.0 x64:
- `agy -p "hi"` → отвечает (было `Eligibility check failed`).
- `agy models` → список моделей, как раньше.
- Бинарь, патченный оригиналом 1.3.8, определяется как `unpatched`
  и допатчивается только недостающими гейтами.

## Использование

```bash
cd ~/open-antigravity-patcher/source
python3 main.py ~/.local/bin/agy
# PATCH -> 3 (Antigravity CLI) — применит 3 гейта
# RESTORE -> 7 — откат из .agybak
```

Версия: `1.3.9` (`patcher/constants.py`, `source/version.txt`).
