# DutyBot

DutyBot is a Telegram bot that manages weekly military duty assignments: it
keeps historical records, automatically generates fair duty schedules,
manages personnel, and publishes duties into a Telegram group topic every
Sunday at 8:00 PM (Asia/Singapore by default).

## Tech Stack

- Python 3.13
- [python-telegram-bot](https://docs.python-telegram-bot.org/) v22+
- PostgreSQL + SQLAlchemy (async) ORM
- Alembic migrations
- APScheduler
- Docker / Railway deployable

## Project Structure

```
.
├── bot.py              # Application entrypoint
├── config.py            # Environment-driven settings
├── scheduler.py          # APScheduler wiring for the weekly job
├── handlers/             # Telegram command & callback handlers
├── services/             # Business logic (scheduling, parsing, stats, ...)
├── database/              # Engine, session, unit of work, repositories
├── models/               # SQLAlchemy ORM models
├── jobs/                  # Scheduled background jobs
├── utils/                 # Logging, formatting, decorators, message helpers
├── alembic/               # Database migrations
├── tests/                 # Unit tests
├── requirements.txt
└── README.md
```

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL 14+ (or Docker)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### Local setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# edit .env with your values (see below)
```

## PostgreSQL Setup

**Locally with Docker:**

```bash
docker run -d --name dutybot-postgres \
  -e POSTGRES_USER=dutybot -e POSTGRES_PASSWORD=dutybot -e POSTGRES_DB=dutybot \
  -p 5432:5432 postgres:16-alpine
```

Then set `DATABASE_URL=postgresql+asyncpg://dutybot:dutybot@localhost:5432/dutybot` in `.env`.

**On Railway:** add a PostgreSQL plugin to your project; Railway will inject
a `DATABASE_URL` variable automatically (DutyBot accepts both the
`postgres://`/`postgresql://` form Railway provides and the
`postgresql+asyncpg://` form directly).

## Environment Variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `DATABASE_URL` | PostgreSQL connection string |
| `ADMIN_IDS` | Comma-separated Telegram user IDs allowed to run admin commands |
| `GROUP_CHAT_ID` | Telegram group chat ID where duties are published |
| `GROUP_TOPIC_ID` | Forum topic (thread) ID inside the group, optional |
| `TIMEZONE` | IANA timezone for scheduling/display, default `Asia/Singapore` |
| `AUTO_DELETE_SECONDS` | Seconds before temporary bot messages self-delete, default `300` |

## Telegram BotFather Setup

1. Open a chat with [@BotFather](https://t.me/BotFather) and send `/newbot`.
2. Choose a name and username for your bot.
3. Copy the token BotFather gives you into `BOT_TOKEN`.
4. Optionally send `/setcommands` to BotFather and register:
   ```
   start - Welcome message and command list
   help - Show command usage
   see_duty - Show current and next week's duty
   see_past - Browse past duty rosters
   stats - Show duty statistics
   personnel - Manage personnel (admin)
   generate - Generate next week's roster (admin)
   publish - Publish the generated roster (admin)
   add_duty - Import a historical duty roster (admin)
   ```
5. Add the bot to your group and make it an admin (needed to pin messages
   and to post into forum topics).

## How to obtain the Group Chat ID

1. Add your bot to the target group.
2. Send any message in the group.
3. Visit `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` in a browser
   (with your bot's real token substituted), or forward a group message to
   [@userinfobot](https://t.me/userinfobot).
4. Look for `"chat":{"id": -100XXXXXXXXXX, ...}` in the response — that
   negative number is your `GROUP_CHAT_ID`.

## How to obtain the Topic ID

Topics only apply to groups with "Topics" enabled (forum-style groups).

1. Open the desired topic in the group.
2. Send a message inside that topic.
3. Check `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` again — the
   message will include `"message_thread_id": N`. That value is your
   `GROUP_TOPIC_ID`.
4. Leave `GROUP_TOPIC_ID` empty to publish to the group's General topic.

## Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Generate a new migration after changing models
alembic revision --autogenerate -m "describe the change"

# Roll back one migration
alembic downgrade -1
```

## Running Locally

```bash
alembic upgrade head
python bot.py
```

## Running with Docker

```bash
docker compose up --build
```

This starts a PostgreSQL container and the bot together. Configure `.env`
first; `docker-compose.yml` overrides `DATABASE_URL` to point at the bundled
Postgres service.

To build and run the bot image standalone (pointing at an external
database):

```bash
docker build -t dutybot .
docker run --env-file .env dutybot
```

## Deploying to Railway

1. Create a new Railway project and add a PostgreSQL plugin.
2. Add a service from this repository; Railway will detect the `Dockerfile`
   (or `railway.json`) automatically.
3. Set the environment variables listed above in the Railway service
   settings (`DATABASE_URL` is auto-populated by the Postgres plugin — link
   it via a variable reference).
4. Deploy. The start command runs `alembic upgrade head` before launching
   the bot, so migrations are applied automatically on every deploy.

## Command Reference

### Everyone

| Command | Description |
|---|---|
| `/start` | Welcome message and command list |
| `/help` | Command usage, admin commands shown if you're an admin |
| `/see_duty` | Shows current and next week's duty roster (auto-deletes after 5 min) |
| `/see_past` | Inline week picker to browse historical rosters (auto-deletes) |
| `/stats` | Duty statistics for every person |

### Admins only (`ADMIN_IDS`)

| Command | Description |
|---|---|
| `/personnel` | Interactive menu: add/edit/remove people, manage phone holders, view inactive personnel and statistics |
| `/generate` | Generate a draft roster for the next week; preview with Publish/Regenerate/Cancel buttons |
| `/publish` | Publish the most recently generated draft immediately |
| `/add_duty` | Paste a historical duty roster; DutyBot parses it, resolves unknown names (create/match/ignore), and saves only after confirmation |

## Fair Scheduling Algorithm

Each week, DutyBot assigns personnel using weighted random selection so that:

- People who have performed a specific duty category the fewest times are
  favoured for that category.
- People who haven't had any duty in the longest time are favoured overall.
- No one is assigned two duties in the same week.
- Categories that require a phone holder (breakfast/lunch/dinner trash and
  ration runs, key duty) are guaranteed at least one phone-owning assignee
  when one is available.
- Anyone left over after all categories are filled is marked `Resting`.

## Automatic Weekly Publish

Every Sunday at 20:00 (configured `TIMEZONE`), DutyBot automatically:

1. Generates a fair roster for the next week (or regenerates the existing
   unpublished draft, if one exists).
2. Saves it to the database.
3. Publishes it to `GROUP_CHAT_ID` / `GROUP_TOPIC_ID`.
4. Pins the published message.
5. Logs the outcome (success or failure) — failures never crash the bot.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run against an in-memory SQLite database and do not require a real
Telegram token or PostgreSQL instance.

## Logging

DutyBot logs to both the console and a rotating file (`dutybot.log` by
default, override with `LOG_FILE`). Imports, schedule generation,
publishing, parsing failures, admin actions, and errors are all logged.
