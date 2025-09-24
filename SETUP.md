# Reddit Bot Setup Guide

## 1. Get Telegram Bot Token
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow the instructions to create your bot
4. Copy the bot token

## 2. Get Reddit API Credentials
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Choose "script" as the app type
4. Fill in the details and create
5. Copy the client ID and secret

## 3. Setup Environment
1. Copy `env_template.txt` to `.env`
2. Fill in your actual credentials:
   - Replace `your_telegram_bot_token_here` with your bot token
   - Replace `your_reddit_client_id_here` with your Reddit client ID
   - Replace `your_reddit_client_secret_here` with your Reddit client secret
   - Replace `your_app_name_here` with your app name
   - Replace `your_secret_key_here` with any random string

## 4. Install Dependencies
```bash
pip install -r requirements.txt
```

## 5. Run the Bot
```bash
python telegram_bot.py
```

## Features
- **Interactive Buttons**: Use `/start` to see buttons
- **Command Recommendations**: Type `/` to see available commands
- **Conversational Flow**: Bot asks for information step by step
- **Better Formatting**: Results with emojis and clear structure
