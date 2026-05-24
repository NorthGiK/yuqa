# Yuqa

Telegram-бот с игрой, постоянным хранилищем состояния, миграциями Alembic и
поддержкой запуска в контейнере.

[English](README.md) | Русский

## Для игроков

Yuqa - это игра внутри Telegram, а не отдельное приложение для телефона или
компьютера.

Играть в неё нужно прямо в Telegram: открываете бота и используете команды,
кнопки и меню. В игре есть профиль, карточки, бои, квесты, кланы, магазин,
баннеры и боевой пропуск. Прогресс сохраняется постоянно, поэтому аккаунт не
сбрасывается после перезапуска сервиса.

Если вы просто играете, разделы ниже про разработку можно не читать. Главное -
Yuqa хранит состояние игры, инвентарь и награды между сессиями.

## Локальная разработка

```bash
make sync
cp .env.example .env
make agent-summary
make db-upgrade
make run
```

По умолчанию бот хранит состояние в SQLite по адресу `data/yuqa/yuqa.db`.
Задайте `DATABASE_URL`, если нужен PostgreSQL или другая база, совместимая с
SQLAlchemy.

Логирование управляется переменными:

- `YUQA_LOG_LEVEL`: стандартный уровень логирования Python, по умолчанию `INFO`
- `YUQA_LOG_FORMAT`: `plain` для локального запуска или `json` для контейнеров
- `YUQA_METRICS_ENABLED`: включает Prometheus endpoint `/metrics`
- `YUQA_METRICS_HOST`: host для bind metrics endpoint, по умолчанию `127.0.0.1`
- `YUQA_METRICS_PORT`: port для metrics endpoint, по умолчанию `9000`

## Структура пакетов

Телеграм-слой разбит на каталоги с пакетами вместо одного большого набора
модулей:

- `src/telegram/router/` - регистрация обработчиков, шаги в wizard-сценариях и
  переиспользуемые представления
- `src/telegram/services/` - выбор хранилища, типизированные контракты миксинов
  и orchestration-миксины
- `src/telegram/texts/` - тексты и вспомогательные функции форматирования
- `src/telegram/ui/` - клавиатуры и inline-разметка

Импортируйте из стабильных корней пакетов:

- `src.telegram.router`
- `src.telegram.services`
- `src.telegram.texts`
- `src.telegram.ui`

Изменяйте реализацию внутри этих каталогов, когда меняется поведение.

## Соглашения по типизации

- Адаптеры репозиториев должны явно объявлять конкретные типы возврата для
  асинхронных методов, даже если они используют небольшой общий базовый класс.
- Миксины telegram-сервисов используют protocol-контракты из
  `src/telegram/services/contracts.py`; обновляйте эти контракты, когда миксину
  нужен новый репозиторий или атрибут сервиса.
- Добавляйте комментарии только рядом с неочевидными runtime-решениями, такими
  как persistence pragmas или побочные эффекты bootstrap-логики. Для обычного
  потока управления лучше использовать type hints и понятные имена.

## Завершение action-квестов

Маршруты могут завершать квесты с cooldown через один вызов сервиса:

```python
await services.complete_action_quest(
    quest=QuestDefinition(
        id=101,
        period=QuestPeriod.DAILY,
        action_type=QuestActionType.CARD_LEVEL_UP,
        reward=QuestReward(coins=25),
        cooldown=timedelta(hours=2),
    ),
    player_id=telegram_id,
)
```

Хелпер проверяет cooldown квеста игрока, выдаёт награду только когда квест
готов и сохраняет время следующего cooldown.

Для обработчиков, которые должны автоматически завершать квест, импортируйте
`quest_init` из `src.telegram.decorators`. Он извлекает id игрока из сообщения
или callback и передаёт выполнение в тот же persistent-путь сервиса квестов.

## Транзакционные записи

Сценарии с записью данных выполняются через защищённую транзакционную обёртку,
чтобы связанные изменения коммитились вместе и откатывались вместе при ошибке.
Так сохраняется согласованность наград квестов, боёв, покупок, изменений
колоды и контента админа, когда несколько игроков действуют одновременно.

## Наблюдаемость

При старте приложение пишет в логи очищенные runtime-настройки, время миграций,
время инициализации сервисов, жизненный цикл Telegram polling и graceful
shutdown. Пароли в database URL скрываются перед записью в лог.

Если `YUQA_METRICS_ENABLED=true`, бот открывает Prometheus endpoint `/metrics`.
Production compose включает этот endpoint внутри сети Docker на `bot:9000`, а
`docker/prometheus.yml` собирает его как job `yuqa-bot`.

Production compose также включает single-node Elasticsearch, Kibana и Filebeat.
Бот пишет JSON-логи в stdout, Docker хранит их с ротацией, а Filebeat отправляет
контейнеры с Yuqa log labels в Elasticsearch, чтобы их можно было искать в
Kibana.

Healthcheck можно запустить отдельно:

```bash
python -m src.infrastructure.sqlalchemy.healthcheck
```

Он печатает один JSON-объект и завершается с ненулевым кодом, если база
недоступна, не созданы runtime-таблицы или версия базы не совпадает с текущим
Alembic head.

## Рабочий процесс AI-агентов

В репозитории есть скрипт и руководство для инспекции:

```bash
make agent-summary
make agent-check
```

- `make agent-summary` выводит компактную JSON-карту entrypoint-ов, фич,
  режимов хранения, стабильных поверхностей пакетов и hotspot-файлов.
- `make agent-check` проверяет несколько границ слоёв, чтобы доменные модули не
  начали зависеть от Telegram или адаптеров хранения.
- `docs/ai-agents.md` даёт самый короткий путь к нужным модулям для runtime,
  transport, domain и persistence задач в текущей структуре пакетов.

## Стресс-тестирование

Локальную рандомизированную симуляцию на уровне сервисов можно запустить так:

```bash
make stress
make stress STRESS_ARGS="--players 100 --operations-per-player 200 --concurrency 50"
```

Скрипт `scripts/stress_app.py` создаёт временную SQLite-базу, наполняет каталог
тестовым контентом, симулирует множество одновременных игроков в профильных,
экономических, коллекционных, квестовых, идейных и боевых сценариях, а затем
выводит JSON-метрики по latency, throughput, ожидаемым domain-rule отказам,
ошибкам, CPU time и памяти. Передайте `--database-url`, если нужно измерить
конкретную базу данных.

## Модель хранения

- ORM-таблицы распределены по `src/infrastructure/sqlalchemy/models/`, а не
  собраны в одном плоском модуле.
- SQLAlchemy-репозитории используют отдельные relational-таблицы для агрегатов,
  а не один JSON-документ со всем состоянием приложения. Миграция переносит
  старые данные из `state_documents` в новые таблицы и затем удаляет legacy
  таблицу.
- Статические данные каталога из `data/yuqa/catalog.json` импортируются в базу
  при первом запуске.
- Runtime-состояние, такое как игроки, карточки, кланы, завершённые бои и
  черновики колод, сохраняется, поэтому рестарт не сбрасывает прогресс.
- Определения квестов и cooldown-ы квестов для каждого игрока также
  сохраняются вместе с runtime-состоянием.
- Активные бои и очереди matchmaking очищаются при старте сервиса, потому что
  timers in combat are runtime-only.
- Alembic управляет изменениями схемы через `make db-upgrade`.

## Docker-развертывание

```bash
docker build -f docker/Dockerfile -t yuqa:latest .
```

Контейнерный образ копирует исходники приложения, запускает `uv sync` во время
сборки, устанавливает зависимости по `uv.lock` и стартует установленный
entrypoint `yuqa`. `.env` не копируется внутрь образа. Образ собран для работы
с PostgreSQL, поэтому при запуске задайте `DATABASE_URL` с PostgreSQL-строкой
подключения. Если вам нужно постоянное состояние вне контейнера, подключайте
`/data` только для каталога или локальных экспериментов.

Для продакшена используйте `docker/compose.yaml`: он поднимает бота и
PostgreSQL вместе. Он также запускает Prometheus для метрик и Elasticsearch,
Kibana и Filebeat для поиска по логам. Контейнер бота работает не от root, с
read-only root filesystem, сброшенными Linux capabilities, `no-new-privileges`,
небольшим `/tmp` tmpfs, JSON-логами, ротацией логов, healthcheck и временем на
graceful stop.

Стандартные URL после `docker compose -f docker/compose.yaml up -d`:

- Prometheus: `http://localhost:9090`
- Kibana: `http://localhost:5601`

## CI/CD

Deployment pipeline должен запускать lint и tests, собирать версионированный
контейнерный образ, передавать production `.env` вне образа и разворачивать
`docker/compose.yaml` через `docker compose up -d --wait`.

Типовые переменные деплоя:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PATH`
- `DEPLOY_SSH_KEY`
- `DEPLOY_ENV_FILE`
