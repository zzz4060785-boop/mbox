# PostgreSQL transition

The application reads `DATABASE_URL` from `.env`. If it is absent, the local
`friendary.db` SQLite database remains in use.

## 1. Create a PostgreSQL database

Create a managed PostgreSQL database with the deployment provider and copy its
connection URL. Do not commit that URL because it includes the database
password.

## 2. Install the PostgreSQL driver

```powershell
pip install -r requirements.txt
```

## 3. Configure the connection

Add the provider URL to the real `.env` file:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
```

Both `postgres://` and `postgresql://` provider URLs are normalized to the
`psycopg` driver by `config.py`.

## 4. Create the schema

Keep a backup of `friendary.db`, then run:

```powershell
$env:FLASK_APP = "pybo"
flask db upgrade
```

This creates the existing application schema in PostgreSQL. Existing SQLite
records must be copied only after this step. Do not delete `friendary.db` until
record counts and application behavior have been verified.
