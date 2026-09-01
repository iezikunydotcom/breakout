# Breakout (rainbow brick-breaker)

Break all the rainbow bricks with the ball. There are two versions:

- `breakout.py` - desktop game (pygame)
- `app.py` - web version with user accounts (Flask + SQLite), where each
  player's best score is saved to their account

## Desktop version

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-desktop.txt
python breakout.py
```

Controls: mouse or arrow keys to move the paddle, P to pause, R to restart.

## Web version with accounts

```powershell
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 and register an account.

## Deploy online (free)

The web version needs a Python-capable host. Use PythonAnywhere (free,
persistent disk) or Render (free, auto-deploys from a private GitHub repo).
See the `game-release` skill's hosting reference for exact steps.

Note: `requirements.txt` contains only the web dependencies on purpose -
`pygame` lives in `requirements-desktop.txt` so the web build never tries
to install it.
