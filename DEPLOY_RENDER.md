# Deploying TBGP Portal on Render

## Option 1: Render Blueprint

1. Push this repository to GitHub.
2. In Render, choose **New +** > **Blueprint**.
3. Select this repository.
4. Render will read `render.yaml`, create:
   - a Python web service named `tbgp-portal`
   - a PostgreSQL database named `tbgp-db`
5. Set `ADMIN_MEMBER_ID` if your production data uses a specific platform/admin member ID.
6. Deploy.

## Option 2: Manual Web Service

Create a Render PostgreSQL database first, then create a Python web service with:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn run:app --bind 0.0.0.0:$PORT`

Required environment variables:

- `DATABASE_URL`: Render PostgreSQL internal connection string
- `SECRET_KEY`: a long random secret value

Optional environment variables:

- `ADMIN_MEMBER_ID`
- `CLIENT_POOL_PERCENT`
- `CONTRACTOR_POOL_PERCENT`
- `ADMIN_ACCOUNT_PERCENT`
- `MEMBER_EARNINGS_CAP_FIRST_PROJECT`
- `MEMBER_EARNINGS_CAP_SECOND_PROJECT`
- `MEMBER_EARNINGS_CAP_NTH_PROJECT`
- `MEMBER_LIFETIME_EARNINGS_CAP`
- `MEMBER_LIFETIME_PROJECT_CAP_AFTER_LIMIT`

## Notes

- The app supports Render's `DATABASE_URL` and still supports local `DB_USER`, `DB_PASS`, `DB_IP`, `DB_PORT`, and `DB_NAME` settings.
- On startup, the app creates missing tables, runs lightweight migrations, and seeds required default users/data.
- Change default seeded account passwords after the first production login.
