# Amul Protein Tracker Bot

A Telegram bot that tracks availability and prices of **all 13 Amul High Protein products** on [shop.amul.com](https://shop.amul.com).

## Features

- **Live product data** — Scrapes shop.amul.com for real-time prices and stock status
- **Availability dashboard** — `/track` shows all products with in-stock/out-of-stock indicators
- **Watchlist** — Watch out-of-stock items and get instant alerts when they return
- **Automatic checks** — Bot scrapes every 6 hours and notifies you of price/stock changes
- **13 products tracked** — Buttermilk, Milk, Lassi, Rose Lassi, Blueberry Shake, Kool (Kesar, Coffee, Chocolate), Whey Protein (Plain/Chocolate sachets & 1kg), High Protein Paneer

## Prerequisites

1. **Telegram Bot Token** — Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. **Your Telegram User ID** — Get it from [@userinfobot](https://t.me/userinfobot)

## Setup

```bash
# Clone
git clone https://github.com/Anoop9290/amul-protein-bot.git
cd amul-protein-bot

# Environment
cp .env.example .env
# Edit .env with your bot token and user ID

# Install
pip install -r requirements.txt
playwright install chromium

# Run
python -m src.main
```

## Docker (recommended for deployment)

```bash
docker build -t amul-tracker .
docker run -d --env-file .env amul-tracker
```

## Deploy to Railway

1. Push to GitHub
2. Create a new project on [railway.app](https://railway.app)
3. Connect your GitHub repo
4. Add environment variables: `TELEGRAM_BOT_TOKEN`, `ADMIN_USER_ID`
5. Deploy — Railway auto-detects the Dockerfile

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message & setup |
| `/products` | Fetch live prices & stock for all 13 products |
| `/track` | Availability dashboard with watch/unwatch buttons |
| `/settings` | Toggle notifications, set pincode |
| `/help` | Help & how tracking works |

## How Tracking Works

```
Every 6 hours:
  Bot scrapes shop.amul.com for all 13 products
    ├─ Price changed? → Sends price alert
    ├─ Stock changed? → Sends stock alert
    └─ Item back in stock + you're watching? → Sends "Back in Stock!" with buy link
```

1. Use `/track` to see the availability dashboard
2. Tap **(+) Watch** on any out-of-stock product
3. Bot checks automatically every 6 hours
4. You get an instant alert when your watched item is back in stock

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | (required) | Bot token from BotFather |
| `ADMIN_USER_ID` | `0` | Your Telegram user ID |
| `DEFAULT_PINCODE` | `380001` | Default delivery pincode |
| `PRICE_CHECK_INTERVAL_HOURS` | `6` | How often to check prices |
| `SCRAPE_CACHE_TTL_MINUTES` | `30` | Cache TTL for scraper |
