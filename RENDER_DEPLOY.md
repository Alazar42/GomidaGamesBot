# Deploy on Render

Create a **Web Service** with these settings:

- Build command: `pip install -r requirements.txt`
- Start command: `python main.py`
- Environment variable: `BOT_TOKEN` (set the current token from BotFather)

Render provides `RENDER_SERVICE_TYPE`, `RENDER_EXTERNAL_URL`, and `PORT` to the web service. The start command launches FastAPI on `0.0.0.0:$PORT`; at startup the app registers `RENDER_EXTERNAL_URL/webhook` with Telegram. If you set `WEBHOOK_URL` explicitly, use the full public URL ending in `/webhook`.

For local polling, run `python main.py` outside Render without `WEBHOOK_URL` or `ENVIRONMENT=production`.

The free web instance can sleep after inactivity, so Telegram requests may be delayed while it wakes. For an always-running polling bot, use a Render Background Worker instead of a Web Service.

If the bot token appeared in logs or screenshots, revoke it through BotFather, set the replacement in Render's Environment page and your local `.env`, then redeploy. Do not commit `.env`.
