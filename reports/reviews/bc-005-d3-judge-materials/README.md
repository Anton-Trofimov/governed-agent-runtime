# BC-005-D3 — запуск двух независимых judge-запросов

Сначала review `judge-system.txt` и `judge-output.schema.json`.
До явного принятия инструкции судьи используйте только offline-команду ниже.
Все пути ниже относятся к WSL Ubuntu; каталог проекта используется только для Python venv.
Никакие AGENTS.md, файлы проекта или история чата в запросы автоматически не загружаются.

1. Распакуйте архив так, чтобы kit находился в
   `~/projects/evidence/governed-agent-runtime/bc-005-d3-judge-kit/`.
2. Проверьте пакет без обращения к Ollama:

```bash
~/projects/governed-agent-runtime/.venv/bin/python ~/projects/evidence/governed-agent-runtime/bc-005-d3-judge-kit/run_judge.py
```

3. После принятия инструкции судьи и при запущенном Ollama выполните ОДИН раз:

```bash
~/projects/governed-agent-runtime/.venv/bin/python ~/projects/evidence/governed-agent-runtime/bc-005-d3-judge-kit/run_judge.py --run --approved-system-sha256 88d7768fbb794cb197676619f141fc5000739a0225a73ee699c51e44a972a7ee
```

Будут ровно два последовательных независимых `/api/chat` запроса (A и B), без
preload и без автоматического retry. В каждом ровно system + user; ответ A
не передаётся в B. `keep_alive` удерживает веса, но не добавляет историю чата.
Cold-start latency A и warm B не сравниваются как качество/скорость кандидатов.

Параметры: qwen3.8:27b; think=true; temperature=1; top_p=.95; top_k=20;
min_p=0; presence_penalty=0; repeat_penalty=1; seed=18; num_ctx=32768;
num_predict=8192; stream=false; keep_alive=10m; timeout=300s.
Перед inference и каждым запросом проверяются Ollama 0.32.14 и точный digest D1.
При несовпадении — остановка, без автоматической смены модели или обновления.

Evidence сохраняется в новом каталоге:
`~/projects/evidence/governed-agent-runtime/bc-005-d3/<UTC-run-id>/`.
Сохраняются exact requests, raw provider responses (включая thinking), finals,
manifest и hashes. Raw записывается до проверки JSON ответа. При timeout результат
выполнения inference может быть неизвестен; скрипт не повторяет запрос.
`.measurement-started.json` защищает от случайного повторного запуска этого kit.
Если запуск остановился — пришлите manifest/ошибку, не запускайте заново.

После завершения пришлите `manifest.json`, `judge-A.exact.json`,
`judge-B.exact.json` и оба `response-*.raw.json`. Вердикты судьи ещё требуют human
проверки оснований; runner не решает, правильна ли семантика оценки.
