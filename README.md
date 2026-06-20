# PHIMA

PHIMA is a Streamlit app configured for deployment on Streamlit Community Cloud.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/).
3. Choose **New app** and select this repository and branch.
4. Set the main file path to `app.py`.
5. Click **Deploy**.

## Deployment files

- `app.py` — Streamlit app entry point.
- `requirements.txt` — Python dependencies installed by Streamlit Community Cloud.
- `packages.txt` — optional system package list for Streamlit Community Cloud.
- `.streamlit/config.toml` — Streamlit runtime configuration.
