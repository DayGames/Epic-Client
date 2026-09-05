# Epic Client

A Windows app store built in Python: one central **backend** (FastAPI) that hosts the
catalog and installer files, and a **desktop GUI client** (PySide6) that browses,
downloads, and uploads apps.

## Folder structure

```
Epic Client/
├── README.md
├── requirements.txt
│
├── server/                  # THE STORE (runs in the cloud / on a host PC)
│   ├── main.py              # FastAPI entry point  ->  uvicorn main:app --reload
│   ├── config.py            # settings (secret key, DB url, file folder)
│   ├── database.py          # SQLAlchemy engine + session
│   ├── models.py            # DB tables: User, App
│   ├── schemas.py           # request/response shapes (Pydantic)
│   ├── auth.py              # password hashing + JWT login tokens
│   ├── routers/
│   │   ├── users.py         # /users/register, /users/login, /users/me
│   │   └── apps.py          # /apps  (list, upload, download)
│   ├── files/               # uploaded installers land here (auto-created)
│   └── epicstore.db         # SQLite database (auto-created)
│
└── client/                  # THE DESKTOP APP (runs on each user's Windows PC)
    ├── main.py              # launches the GUI  ->  python main.py
    ├── config.py            # SERVER_URL + download folder
    ├── api.py               # talks to the backend over HTTP
    └── ui/
        ├── login_window.py  # sign in / register
        └── store_window.py  # browse, download, upload
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run the backend

```bash
cd server
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs to see and test the API.

## Run the desktop client

In a second terminal (backend still running):

```bash
cd client
python main.py
```

Register an account, log in, then browse / upload / download apps.

## Package the client into a .exe (optional, later)

```bash
cd client
pyinstaller --noconsole --onefile main.py
```

## Next steps / ideas
- Track installed apps + versions on the client so it can show "Update available".
- Add app icons and screenshots.
- Move from SQLite to PostgreSQL and files to Cloudflare R2 for real hosting.
- Add an `is_admin` check so only approved users can upload.
```
