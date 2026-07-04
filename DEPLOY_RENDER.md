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
- Start command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`

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

## Custom Domain Name

After the web service is deployed and working on the default Render URL, add your own domain:

1. Open the Render dashboard.
2. Select the `tbgp-portal` web service.
3. Go to **Settings** > **Custom Domains**.
4. Click **Add Custom Domain**.
5. Enter the domain you want to use, for example:
   - `portal.example.com`
   - `www.example.com`
   - `example.com`
6. Render will show the DNS record you need to create at your domain provider.

For a subdomain such as `portal.example.com` or `www.example.com`, create a `CNAME` record:

- Type: `CNAME`
- Name/Host: `portal` or `www`
- Value/Target: the Render hostname shown in the dashboard

For a root/apex domain such as `example.com`, follow Render's displayed DNS instructions. Many DNS providers support `ALIAS`, `ANAME`, or flattened `CNAME` records for root domains. If your provider does not support this, use `www.example.com` as the main domain and redirect the root domain to `www`.

After saving DNS records:

1. Return to Render's **Custom Domains** page.
2. Wait for the domain status to become verified.
3. Render will automatically issue an SSL certificate.
4. Use `https://your-domain.com` after the certificate is active.

DNS changes can take a few minutes to several hours depending on the domain provider.

## Notes

- The app supports Render's `DATABASE_URL` and still supports local `DB_USER`, `DB_PASS`, `DB_IP`, `DB_PORT`, and `DB_NAME` settings.
- On startup, the app creates missing tables, runs lightweight migrations, and seeds required default users/data.
- Change default seeded account passwords after the first production login.
- If Render logs show `gunicorn.errors.AppImportError: Failed to find attribute 'app' in 'app'`, update the Render **Start Command** to `gunicorn wsgi:app --bind 0.0.0.0:$PORT`.
