=== НАЧАЛО ===
# OpenCode Ensemble

Универсальный ансамбль бесплатных моделей OpenCode для автоматической генерации, проверки и доработки кода в любом проекте. Содержит 4 генератора, 2 независимых судьи, байесовские веса, калибровку уверенности и мета-роутер для выбора лучших моделей под задачу.

## Содержание

- [Быстрый старт](#быстрый-старт)
- [Установка OpenCode и запуск сервера](#установка-opencode-и-запуск-сервера)
- [Установка ансамбля](#установка-ансамбля)
- [Использование в любом проекте](#использование-в-любом-проекте)
- [Прямое общение с OpenCode](#прямое-общение-с-opencode)
- [Как это работает](#как-это-работает)
- [Настройка моделей](#настройка-моделей)
- [Максимизация эффективности](#максимизация-эффективности)
- [Устранение проблем](#устранение-проблем)

---

## Быстрый старт

Три команды для тех, кто уже знает, что делает:

```powershell
opencode serve --hostname 127.0.0.1 --port 4096
git clone https://github.com/ФОМЕНКО/opencode-ensemble.git
cd opencode-ensemble; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

Подробности — в разделах ниже.

---

## Требования

| Что | Версия / примечание |
|---|---|
| Python | 3.10+ |
| Git | любая современная версия |
| OpenCode CLI | актуальная, с моделями `opencode/*-free` |
| ОС | Windows, Linux, macOS |
| GPU | не требуется — модели работают в облаке OpenCode |

---

## Установка OpenCode и запуск сервера

### 1. Установка

**Windows (PowerShell):**
```powershell
npm install -g opencode-ai
opencode --version
```

**Linux / macOS:**
```bash
curl -fsSL https://opencode.ai/install | bash
opencode --version
```

**Проверка моделей:**
```powershell
opencode models
```
В списке должны быть модели с суффиксом `-free`.

### 2. Запуск сервера

В **отдельном окне терминала** (не закрывать, пока идёт работа):
```powershell
opencode serve --hostname 127.0.0.1 --port 4096
```

Если нужен пароль:
```powershell
$env:OPENCODE_SERVER_PASSWORD="mypassword"
opencode serve --hostname 127.0.0.1 --port 4096
```

### 3. Проверка соединения

В основном окне:
```powershell
opencode run --server http://127.0.0.1:4096 -m opencode/nemotron-3.5-super-vl-free --auto "Ответь: ok"
```
Должно вернуть `ok`. Если `Connection refused` — сервер не запущен.

---

## Установка ансамбля

### 1. Клонирование
```powershell
cd C:\Users\AF\PycharmProjects
git clone https://github.com/ФОМЕНКО/opencode-ensemble.git
cd opencode-ensemble
```

### 2. Зависимости
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
`requirements.txt` содержит `numpy`, `scikit-learn`, `pytest`. Torch не нужен — модели работают в облаке OpenCode.

### 3. Проверка структуры
```powershell
Get-ChildItem
```
Должно быть:
```text
ensemble\
specs\
acceptance\
models.json
requirements.txt
README.md
```

### 4. Готово
Ансамбль установлен. Переходите к использованию.

---

## Использование в любом проекте

### Требование к проекту
Проект должен быть git-репозиторием **с хотя бы одним коммитом**. Если нет:
```powershell
cd C:\Путь\К\Проекту
git init
git add .
git commit -m "initial"
```

### Шаг 1. Создать спецификацию
Файл `C:\Users\AF\PycharmProjects\opencode-ensemble\specs\TASK.md`:
```markdown
# Задача
Добавь в файл `main.py` функцию `add(a, b)`, возвращающую сумму.
Не меняй остальные файлы.
```

### Шаг 2. Создать приёмочные тесты
Файл `C:\Users\AF\PycharmProjects\opencode-ensemble\acceptance\test_TASK.py`:
```python
def test_add():
    from main import add
    assert add(2, 2) == 4
    assert add(-1, 5) == 4
```

### Шаг 3. Запустить ансамбль
```powershell
cd C:\Users\AF\PycharmProjects\opencode-ensemble
.\.venv\Scripts\Activate.ps1
python ensemble\run_ensemble.py all --project C:\Путь\К\Проекту --wp TASK --spec specs\TASK.md --test acceptance\test_TASK.py --parallel 2 --rounds 2
```
В консоли побегут строки `[TASK] <модель> rN: unit Xp/Yf`, в конце появится:
```text
borda: {...}
WINNER: <имя_победителя>
```

### Шаг 4. Слить результат
```powershell
cd C:\Путь\К\Проекту
git diff main ens/TASK/<победитель> -- <файл>
git merge ens/TASK/<победитель>
python -m pytest "C:\Users\AF\PycharmProjects\opencode-ensemble\acceptance\test_TASK.py" -q
```
Ожидаемо: `1 passed`.

### Шаг 5. Очистить ветки
```powershell
git for-each-ref --format='%(refname:short)' 'refs/heads/ens/TASK/*' | ForEach-Object { git branch -D $_ }
```

---

## Прямое общение с OpenCode

Ансамбль — это автоматизация, но с OpenCode можно работать и напрямую.

### Интерактивный режим (TUI)
```powershell
opencode
```
Внутри пишете запрос, Enter. Модель читает файлы, правит код, запускает команды. Выход — `Ctrl+C`.

### Headless (одна команда)
```powershell
opencode run --server http://127.0.0.1:4096 -m opencode/nemotron-3.5-super-vl-free --auto "Прочитай TASK.md и выполни задачу"
```

Полезные флаги:
| Флаг | Назначение |
|---|---|
| `--auto` | авто-подтверждение разрешений |
| `--format json` | машиночитаемый вывод |
| `--continue` | продолжить последнюю сессию |
| `--session <id>` | конкретная сессия |
| `--file <path>` | прикрепить файл |

### Attach (TUI к серверу)
```powershell
opencode attach http://127.0.0.1:4096 --dir C:\Путь\К\Проекту
```

### Как формулировать запрос
- **Контекст:** «Прочитай TASK.md, SPEC.md, файлы X, Y».
- **Задача:** «Добавь функцию…», «Исправь ошибку…».
- **Ограничения:** «Не меняй acceptance/specs», «Не делай git commit».
- **Проверка:** «Запусти `python -m pytest acceptance/test_TASK.py -q`».

---

## Как это работает

### Архитектура
| Файл | Назначение |
|---|---|
| `ensemble/run_ensemble.py` | Оркестратор: генерация, тесты, судьи, слияние, доработка |
| `ensemble/bayesian.py` | Байесовские веса моделей (Beta-Bernoulli) |
| `ensemble/calibration.py` | Калибровка уверенности (Platt scaling) |
| `ensemble/meta_router.py` | Мета-роутер: выбор 2 моделей под задачу (после 6+ задач) |
| `ensemble/visual_diagnose.py` | Визуальная диагностика (опционально) |
| `models.json` | Список генераторов, судей, слиятеля |
| `specs/` | Спецификации задач |
| `acceptance/` | Приёмочные тесты |

### Конвейер
1. **Generate:** 4 модели параллельно пишут код в изолированных worktree.
2. **Verify:** запускается `pytest`, результат — `passed`/`failed`.
3. **Diagnose:** если в проекте есть `diagnose.py`, запускается визуальная проверка.
4. **Judge:** 2 судьи ранжируют решения (Borda с байесовскими весами).
5. **Fuse:** победитель объединяется с лучшими идеями проигравших.
6. **Refine:** финальный проход «старшего инженера».

### Автоматика
- **429 rate limit:** если модель упёрлась в лимит, раунды не тратятся, модель пропускается.
- **BOM:** при копировании spec/acceptance в worktree снимается BOM.
- **Служебные файлы:** `specs/`, `acceptance/`, `__pycache__/`, `*.pyc` не попадают в коммит кандидата.

### После 6+ задач
Мета-роутер начинает выбирать 2 модели вместо 4, экономя запросы и время. Калибровка начинает корректировать голоса судей на основе истории.

---

## Настройка моделей

Файл `models.json`:
```json
{
  "generators": [
    "opencode/deepseek-v4.1-flash-free",
    "opencode/glm-5.3-flash-free",
    "opencode/mimo-v2.6-flash-free",
    "opencode/nemotron-3.5-super-vl-free"
  ],
  "judges": [
    "opencode/beam-free",
    "opencode/nemotron-3.5-lightning-free"
  ],
  "fuser": "opencode/glm-5.3-flash-free"
}
```

| Поле | Что означает |
|---|---|
| `generators` | 4 модели, которые пишут код параллельно |
| `judges` | 2 модели, которые оценивают решения |
| `fuser` | 1 модель, которая объединяет идеи |

Можно менять состав на любой (любые модели из `opencode models`).

---

## Максимизация эффективности

### При 429 (лимит OpenCode)
Запускать с явным списком доступных моделей и меньшим числом раундов:
```powershell
python ensemble\run_ensemble.py all --project ... --wp TASK --spec ... --test ... --models opencode/nemotron-3.5-super-vl-free,opencode/deepseek-v4.1-flash-free --rounds 0 --parallel 1
```

### Проверка квоты
```powershell
opencode run -m opencode/deepseek-v4.1-flash-free --auto "ok"
```
Если `429` — подождать. `retryAfterMs` в логе покажет точное время.

### Что можно улучшить дальше
- **Fallback на OpenRouter/Ollama:** добавить провайдера в `opencode.json`, включить в `models.json`. Снимает лимиты OpenCode.
- **Кэширование:** если задача повторяется, брать готовую ветку.
- **Разные `--rounds` для разных задач:** 0 для простых, 3 для сложных.
- **Ротация судей:** менять `judges` между задачами.

---

## Устранение проблем

| Симптом | Причина | Решение |
|---|---|---|
| `429 FreeUsageLimitError` | Лимит бесплатных моделей | Ждать `retryAfterMs` или сменить модель |
| `pytest не запустился` | BOM в `test_*.py` | `run_ensemble.py` снимает BOM через `utf-8-sig` |
| `invalid reference: HEAD` | В целевом проекте нет коммитов | `git add . && git commit -m "init"` |
| `not something we can merge` | Merge выполняется не в том репозитории | Merge только в целевом проекте |
| `ModuleNotFoundError: main` | pytest запущен не из папки проекта | Абсолютный путь к тесту или `cd` в проект |
| `visual_ok=True` при `unit_ok=False` | Старый баг | Проверить `visual_ok = False` в `if not res["ok"]` |

---

## Лицензия

Проект распространяется свободно для научных и учебных целей.
=== КОНЕЦ ===