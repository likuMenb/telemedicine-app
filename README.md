# Ne

## Streamlit app (this folder)

```powershell
cd C:\Users\user\Documents\Ne
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

- Copy `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` if you need your own keys.
- First time: open the app’s **Database setup** tab and run the SQL in Supabase.

### Streamlit Community Cloud (e.g. `*.streamlit.app`)

1. **Repo layout**: `app.py` and **`requirements.txt` must live in the main module folder** GitHub clones (typically the repo **root**, same level as each other — not tucked under `your_project/` only).
2. **Secrets**: in the deployed app → **Settings → Secrets**, paste:

   ```toml
   SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
   SUPABASE_KEY = "YOUR_ANON_OR_PUBLISHABLE_KEY"
   ```

   Optional:

   ```toml
   [default]
   app_name = "CareStream Tasks"
   ```

3. **Logs**: Lines like **`ConnectionClosedError` / websocket keepalive** often appear after a redeploy or a dropped tab refresh; fix real errors first (**ModuleNotFound**, missing secrets). Hard-refresh the app URL after each deploy.

## Other projects here

- **`telemed/`** — Next.js telemedicine demo (see `telemed/README.md`).
- **`your_project/`** — older copy of the Streamlit demo; use **`app.py` in this root** instead.
