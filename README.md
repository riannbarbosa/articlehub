<div align="center">

# 📚 ScholarHub

**Your personal academic research hub.**

Organize scientific papers, take structured notes, capture insights, and
visualize everything as a knowledge graph.

[![Python](https://img.shields.io/badge/Python-3.9-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-3.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![SQLite](https://img.shields.io/badge/SQLite-PostgreSQL-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#-license)

</div>

---

## ✨ What is it

**ScholarHub** is a Django web app for students, researchers, and academics who
read a lot of papers and need a single place to keep references, notes, and
ideas — all connected. Instead of scattered folders and loose PDFs, you get a
navigable knowledge base.

## 🚀 Features

| | Feature | Description |
|---|---|---|
| 📄 | **Papers** | Save papers with title, author, year, link, DOI, and a quality rating (Poor → Excellent). |
| 🔎 | **Automatic DOI lookup** | Paste a DOI and ScholarHub fills in the metadata via the [Crossref API](https://api.crossref.org). |
| 📝 | **Notes** | One rich note per paper to record your reading, summary, and key points. |
| 💡 | **Ideas / Insights** | Jot down ideas and link them to the papers that inspired them. |
| 🏷️ | **Tags** | Tag papers and ideas with reusable labels and filter by topic. |
| 🕸️ | **Knowledge graph** | A graph view connecting papers, notes, insights, and tags. |
| 🔐 | **OTP authentication** | Sign up with email code confirmation, plus password recovery. |
| 📱 | **Responsive** | Works great on desktop and mobile. |

## 🛠️ Stack

- **Backend:** Django 3.1 · Python 3.9
- **Database:** SQLite by default (zero config) · PostgreSQL optional
- **Integrations:** Crossref (DOI metadata) · Resend/SMTP (OTP email)
- **Frontend:** Django templates + interactive in-browser graph

## ⚡ Getting started

### 1. Clone and enter the project

```bash
git clone git@github.com:riannbarbosa/articlehub.git
cd articlehub
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv env
source env/bin/activate        # Windows: env\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Generate a `SECRET_KEY` and paste it into `.env`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> 💡 `.env.example` documents every option: database (SQLite/PostgreSQL),
> `ALLOWED_HOSTS`, and email delivery (Resend, SMTP, or console).

### 4. Set up the database and create an admin user

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run the server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** 🎉

> Without email configured, the sign-up OTP code is printed straight to the
> terminal — perfect for local development.

## 🗺️ Main routes

| Path | What it does |
|---|---|
| `/` | Login |
| `/register/` · `/verify/` | Sign-up and OTP confirmation |
| `/artigos/` | List, create, and filter papers |
| `/artigos/<id>/fichamento/` | Paper notes |
| `/ideias/` | Your ideas and insights |
| `/grafo/` | Knowledge graph |
| `/admin/` | Django admin panel |

## 🧱 Project structure

```
articlehub/
├── scholarhub/      # Django project config (settings, urls, wsgi/asgi)
├── main/            # Auth, OTP, password recovery, and the graph
├── articles/        # Papers, notes, tags, and the Crossref client
├── ideas/           # Ideas and insights linked to papers
├── templates/       # Base templates and error pages
└── manage.py
```

## 📄 License

Distributed under the MIT License.

---

<div align="center">
Built with ☕ and Django.
</div>
