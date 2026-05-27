# README — Friends of Poway Seniors (FOPS) Backend

> This is the Flask backend server powering the **Friends of Poway Seniors (FOPS)** web platform — a nonprofit organization in Poway, California that supports seniors through programs like BINGO, Social Lunch, and the ReRuns Shoppe. This project was built on top of the AP CSP / Data Structures Flask starter template and extended with volunteer management, reservations, an AI chatbot, and event RSVP functionality.

## What This Project Does

- **Volunteer signup APIs** for three programs: BINGO, ReRuns Shoppe, and Social Lunch
- **Lunch reservation system** for Social Lunch attendees
- **AI-powered chatbot** (`/api/chat`) that answers questions about FOPS programs using Google Gemini (with a keyword-based fallback)
- **Event RSVP system** via a separate `chatbot.py` blueprint using a `fops.db` SQLite database
- **User authentication** using JWT cookies and Flask-Login
- **MicroBlog / social post APIs** for community interaction
- **Admin routes** for managing users, sections, personas, analytics, and more
- **KASM integration** for managing virtual desktop users
- **Deployment-ready** for AWS, Docker, Nginx, and WSGI

---

## Project Structure

```
flask/
├── main.py                  # App entry point — routes, volunteer DBs, chatbot, CORS config
├── chatbot.py               # Blueprint: event DB, RSVP system, DeepSeek/fallback chatbot
├── __init__.py              # Flask app + DB initialization
├── api/                     # All REST API blueprints (user, gemini, microblog, etc.)
├── model/                   # SQLAlchemy models (User, Post, MicroBlog, etc.)
├── templates/               # Jinja2 HTML templates (login, admin pages, FOPS pages)
├── static/                  # JS/CSS/image assets
├── scripts/                 # DB init and migration scripts
├── instance/volumes/        # SQLite database files (local persistence)
├── bingo_volunteers.db      # Standalone SQLite DB for BINGO volunteers
├── reruns_volunteers.db     # Standalone SQLite DB for ReRuns Shoppe volunteers
├── social_lunch_volunteers.db # Standalone SQLite DB for Social Lunch volunteers
└── fops.db                  # SQLite DB for chatbot events and RSVPs
```

---

## Getting Started

> Requires Python 3.9+ on MacOS, WSL Ubuntu, or Ubuntu.

### 1. Clone and enter the project

```bash
git clone https://github.com/open-coding-society/flask.git
cd flask
```

### 2. Set up a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create your `.env` file

Create a `.env` file in the project root with the following:

```shell
# Port configuration (optional override)
# FLASK_PORT=8376

# Default password for user resets
DEFAULT_PASSWORD='123Qwerty!'
DEFAULT_PFP='default.png'

# Seeded admin user
ADMIN_USER='Thomas Edison'
ADMIN_UID='toby'
ADMIN_PASSWORD='123Toby!'
ADMIN_PFP='toby.png'

# Seeded teacher user
TEACHER_USER='Nikola Tesla'
TEACHER_UID='niko'
TEACHER_PASSWORD='123Niko!'
TEACHER_PFP='niko.png'

# Seeded default test user
USER_NAME='Grace Hopper'
USER_UID='hop'
USER_PASSWORD='123Hop!'
USER_PFP='hop.png'

# Your personal convenience user
MY_NAME='John Mortensen'
MY_UID='jm1021'
MY_ROLE='admin'

# Google Gemini API — used by chatbot and /api/gemini
# Get key at: https://aistudio.google.com/api-keys
GEMINI_API_KEY=xxxxx
GEMINI_SERVER=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent

# Groq API — alternative AI endpoint
# Get key at: https://console.groq.com/keys
GROQ_API_KEY=xxxxx
GROQ_SERVER=https://api.groq.com/openai/v1/chat/completions

# GitHub integration
GITHUB_TOKEN=ghp_xxx
GITHUB_TARGET_TYPE=user
GITHUB_TARGET_NAME=Open-Coding-Society

# KASM virtual desktop configuration
KASM_SERVER=https://kasm.opencodingsociety.com
KASM_API_KEY_SECRET=xxxx
KASM_API_KEY=xxx

# Database mode
IS_PRODUCTION=false   # false = SQLite local, true = AWS RDS
DB_USERNAME='admin'
DB_PASSWORD='xxxxx'
```

### 4. Initialize the database

```bash
python scripts/db_init.py
```

This creates `instance/volumes/user_management.db` with seeded users, personas, and microblog data.
The FOPS-specific databases (`bingo_volunteers.db`, `reruns_volunteers.db`, `social_lunch_volunteers.db`, `fops.db`) are auto-created when the app starts.

### 5. Run the app

```bash
python main.py
```

The server starts at **http://localhost:8376**. Login with credentials from your `.env`.

---

## FOPS-Specific Features

### Volunteer Management

Three separate SQLite databases handle volunteer signups for each program. Each has its own set of tables for volunteer info, availability days, preferred roles, and (where applicable) scheduling.

| Program | Database | Tables |
|---|---|---|
| BINGO | `bingo_volunteers.db` | `volunteers`, `volunteer_availability`, `volunteer_roles`, `volunteer_schedule` |
| ReRuns Shoppe | `reruns_volunteers.db` | `reruns_volunteers`, `reruns_availability`, `reruns_roles` |
| Social Lunch | `social_lunch_volunteers.db` | `social_lunch_volunteers`, `social_lunch_availability`, `social_lunch_roles`, `lunch_reservations` |

### Chatbot

Two chatbot systems exist in this project:

**1. `/api/chat` (defined in `main.py`)**
Uses Google Gemini (`gemini-pro`) when a valid `GEMINI_API_KEY` is set. Falls back to keyword-matching if Gemini is unavailable. Knows about BINGO, Social Lunch, ReRuns Shoppe, volunteering, donations, hours, and contact info.

**2. `/api/chat` (defined in `chatbot.py` blueprint)**
Uses a DeepSeek API endpoint with a fallback. Pulls live event data from `fops.db` and injects it into the system prompt. Supports RSVP actions parsed from AI responses using `[ACTION:RSVP:event_id:name:phone]` syntax.

> ⚠️ Both blueprints register the same `/api/chat` route. The `chatbot_bp` blueprint (registered last in `main.py`) takes precedence.

### Event RSVP System (`fops.db`)

Managed by `chatbot.py`. Tables:

- `events` — stores upcoming events with capacity, date, time, and location
- `rsvps` — records user registrations with duplicate prevention and capacity enforcement

On first run, four sample events are seeded automatically (Senior Lunch, BINGO, Tax Prep, etc.).

---

## API Reference

### FOPS Volunteer & Event APIs

#### BINGO
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/bingo/volunteer` | None | Submit volunteer application |
| GET | `/api/bingo/volunteers` | None | List all volunteers |
| PUT | `/api/bingo/volunteer/<id>/status` | Admin | Update volunteer status |
| GET | `/api/bingo/stats` | None | Volunteer count by status |
| GET | `/api/bingo/test` | None | Health check |

#### ReRuns Shoppe
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/reruns/volunteer` | None | Submit volunteer application |
| GET | `/api/reruns/volunteers` | None | List all volunteers |
| PUT | `/api/reruns/volunteer/<id>/status` | Admin | Update volunteer status |
| GET | `/api/reruns/stats` | Admin | Volunteer stats |
| GET | `/api/reruns/test` | None | Health check |

#### Social Lunch
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/social-lunch/volunteer` | None | Submit volunteer application |
| POST | `/api/social-lunch/reserve` | None | Make a lunch reservation |
| GET | `/api/social-lunch/volunteers` | Admin | List all volunteers |
| GET | `/api/social-lunch/reservations` | Admin | List reservations (filter by `?date=`) |
| PUT | `/api/social-lunch/volunteer/<id>/status` | Admin | Update volunteer status |
| GET | `/api/social-lunch/stats` | Admin | Volunteer and reservation counts |
| GET | `/api/social-lunch/test` | None | Health check |

#### Chatbot & Events
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/chat` | None | Send a message to the FOPS chatbot |
| GET | `/api/chat/test` | None | Check chatbot health + Gemini status |
| GET | `/api/events` | None | List upcoming events from `fops.db` |
| GET | `/api/rsvps` | None | List RSVPs (filter by `?event_id=`) |

### Core Platform APIs (inherited from Flask starter)

#### User Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/authenticate` | Login — sets JWT cookie |
| GET | `/api/id` | Get current logged-in user |
| POST | `/api/user` | Create new user account |
| GET | `/api/post/all` | Get all social posts |
| POST | `/api/post` | Create a social post |
| POST | `/api/gemini` | Chat with Gemini AI |

#### MicroBlog
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/microblog` | Create post |
| GET | `/api/microblog` | Get posts (filter: `?topicId=`, `?userId=`, `?search=`, `?limit=`) |
| PUT | `/api/microblog` | Update post |
| DELETE | `/api/microblog` | Delete post |
| POST | `/api/microblog/reply` | Add reply |
| POST | `/api/microblog/reaction` | Add reaction |
| DELETE | `/api/microblog/reaction` | Remove reaction |

---

## Page Routes

| Route | Template | Description |
|---|---|---|
| `/` | `index.html` | Home page |
| `/login` | `login.html` | Login form |
| `/fopsbingo` | `fopsbingo.html` | BINGO volunteer signup page |
| `/fopsshop` | `fopsshop.html` | ReRuns Shoppe volunteer page |
| `/fopslunchmd` | `fopslunchmd.html` | Social Lunch reservation + volunteer page |
| `/studytracker` | `studytracker.html` | Study tracker UI |
| `/users/table2` | `u2table.html` | Admin user table |
| `/sections/` | `sections.html` | Sections admin view |
| `/kasm_users` | `kasm_users.html` | KASM virtual desktop users |

---

## CORS Configuration

The server allows cross-origin requests from these frontend dev origins:

- `http://localhost:4500`
- `http://localhost:4000`
- `http://localhost:8376`

Update the CORS config in `main.py` if your frontend runs on a different port.

---

## Database Management

### Local Development Workflow

```bash
# 1. Initialize clean local database
python scripts/db_init.py

# 2. Pull real data from production
python scripts/db_migrate-prod2sqlite.py

# 3. Test your changes locally — thoroughly!

# 4. On production server (via Cockpit):
cp sqlite.db backups/sqlite_YYYY-MM-DD.db
git pull
python scripts/db_init.py

# 5. Push local DB to production (requires prod ADMIN_PASSWORD in .env)
python scripts/db_restore-sqlite2prod.py
```

> The four FOPS-specific databases (`bingo_volunteers.db`, `reruns_volunteers.db`, `social_lunch_volunteers.db`, `fops.db`) are managed separately from the main `user_management.db` and are not part of the migration scripts. Back them up manually if needed.

---

## Deployment

This project is configured for production deployment with:

- **Docker + docker-compose** for containerization
- **Nginx** as a reverse proxy
- **Gunicorn** as the WSGI server
- **AWS RDS** for the production database (set `IS_PRODUCTION=true` in `.env`)

Set `IS_PRODUCTION=true` and configure `DB_USERNAME` / `DB_PASSWORD` to switch from SQLite to RDS.

---

## Additional Resources

- [Python/Flask Project Docs](https://pages.opencodingsociety.com/python/flask)
- [Legacy Flask Intro](https://pages.opencodingsociety.com/flask-overview)
- [GitHub Repository](https://github.com/open-coding-society/flask)
- [Google AI Studio (Gemini Keys)](https://aistudio.google.com/api-keys)
- [Groq Console (API Keys)](https://console.groq.com/keys)
