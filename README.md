## Telegram Bot Setup

### Local Development

Environment variables required (create a `.env` file in the project root):

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
REDDIT_CLIENT_ID=your_reddit_app_client_id
REDDIT_CLIENT_SECRET=your_reddit_app_client_secret
REDDIT_USER_AGENT=your_app_name_by_username
```

Install dependencies (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the Telegram bot:

```powershell
python telegram_bot.py
```

### Railway Deployment

1. **Create a new Railway project:**
   - Go to [Railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Connect your GitHub account and select this repository

2. **Set environment variables in Railway:**
   - Go to your project dashboard
   - Click on "Variables" tab
   - Add these environment variables:
     - `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather
     - `REDDIT_CLIENT_ID` - Your Reddit app client ID
     - `REDDIT_CLIENT_SECRET` - Your Reddit app client secret
     - `REDDIT_USER_AGENT` - Your Reddit app user agent

3. **Deploy:**
   - Railway will automatically detect the `railway.json` configuration
   - The bot will start automatically after deployment
   - Check the logs in Railway dashboard to ensure it's running

4. **Get your bot token:**
   - Message @BotFather on Telegram
   - Use `/newbot` command
   - Follow the prompts to create your bot
   - Copy the token and add it to Railway environment variables

### Commands available in Telegram:

- `/start` – greet and overview
- `/help` – show usage
- `/user_details <username> [days]`
- `/user_top <username> [keywords] [limit]`
- `/subreddit_hot <subreddit> [keywords] [limit]`
- `/subreddit_top <subreddit> [keywords] [limit]`


