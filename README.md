# Project B-16 — Social Posts & Messaging Platform

**Project B-16** is a lightweight Django-based social posting and messaging platform designed for rapid development and deployment. It provides user profiles, image-backed posts, threaded messaging, basic moderation tools, and an administrative dashboard — making it ideal for small communities and prototypes.

---

## Key Features ✅

- **User accounts & profiles** with avatars and nickname/onboarding support
- **Image posts** with categories, descriptions, and moderation flags
- **Threaded messaging** (direct messages and group threads) with inbox and thread views
- **Admin dashboard** for content moderation and management
- **Media handling** (local `media/` storage by default; optional S3 support via `django-storages`)
- **Production-ready defaults** for Heroku (Gunicorn) and optional Postgres configuration

## Tech Stack 🔧

- Python + Django
- SQLite (default, suitable for development)
- Optional: Postgres, AWS S3 for media, Heroku deployment
- Key dependencies: `django`, `django-allauth`, `Pillow`, `django-storages`, `boto3`, `gunicorn`

## Quickstart — Local Development 💡

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate # macOS / Linux
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run database migrations and create a superuser:

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. Start the development server:

   ```bash
   python manage.py runserver
   ```

5. Visit http://127.0.0.1:8000 to explore the app.

## Running Tests 🧪

Execute unit tests with:

```bash
python manage.py test
```

## Deployment Notes 🚀

- The app includes a `Procfile` and Gunicorn in `requirements.txt` to simplify Heroku deployment.
- For production media storage, configure `django-storages` and S3 (`boto3`) and set the relevant environment variables.
- Use the `settings/` package to manage environment-specific settings (`dev.py`, `prod.py`, `base.py`). Consider using `python-decouple` or environment variables for secrets.

## Project Structure (high level) 📂

- `app/` — core Django app: models, views, urls, middleware, templates
- `messaging/` — messaging app: models, views, forms, templates
- `media/` — uploaded avatars and post images
- `templates/` — site templates and admin views

