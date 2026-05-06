# Amul High Protein Auto-Order Telegram Bot

A personal Telegram bot that tracks Amul high protein product availability and prices on [shop.amul.com](https://shop.amul.com), sends scheduled weekly reminders, and prepares your shopping cart with one tap so you only need to complete payment.

## Features

- **Live product tracking** — scrapes shop.amul.com for real-time prices and stock status
- **One-tap ordering** — select products and quantities via inline buttons; the bot adds them to your cart automatically
- **Scheduled reminders** — configure weekly reminders (e.g. every Monday at 9 AM) with "Order Now" / "Skip" buttons
- **Price & stock alerts** — get notified when prices change or items go in/out of stock
- **Order history** — view past orders and their checkout links

### Supported Products

| Product | Pack | Protein |
|---------|------|---------|
| High Protein Buttermilk | 200ml x 30 | 15g / 200ml |
| High Protein Milk | 250ml x 32 | 35g / 250ml |
| High Protein Lassi | 200ml x 30 | 15g / 200ml |
| High Protein Rose Lassi | 200ml x 30 | 15g / 200ml |
| High Protein Blueberry Shake | 200ml x 30 | 15g / 200ml |

## Prerequisites

- Python 3.10+
- A Telegram Bot token (see setup below)
- Chromium browser (installed automatically by Playwright)

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts to name your bot
3. Copy the **bot token** BotFather gives you

### 2. Get Your Telegram User ID

1. Search for **@userinfobot** on Telegram
2. Send `/start` — it will reply with your user ID
3. Copy the numeric ID

### 3. Configure the Bot

```bash
cd bot
cp .env.example .env
```

Edit `.env` and fill in:

```
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
ADMIN_USER_ID=your-telegram-user-id
DEFAULT_PINCODE=your-delivery-pincode
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 5. Run the Bot

```bash
python -m src.main
```

The bot will start polling for messages and run scheduled jobs in the background.

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and setup |
| `/products` | Show all products with live prices and stock status |
| `/order` | Select products, set quantities, and prepare your cart |
| `/schedule` | Set up weekly order reminders |
| `/myorders` | View your recent order history |
| `/settings` | Configure pincode and notification preferences |
| `/help` | Show command reference |
| `/cancel` | Cancel any active conversation |

## How It Works

```
You (Telegram)  -->  Bot  -->  Playwright  -->  shop.amul.com
        |                           |
   Commands &            Scrapes prices,
   Callbacks             adds to cart
        |                           |
   Gets reminder        Returns checkout
   with buttons         URL to you
        |                           |
   Taps "Order Now"    You open link in
                       browser & pay
```

1. The bot periodically scrapes shop.amul.com for product prices and availability
2. When you tap "Order Now" (from a reminder or `/order`), Playwright opens a headless browser, navigates to the shop, and adds your selected products to the cart
3. The bot returns the checkout URL — you open it in your browser to log in and complete payment
4. No Amul credentials are stored by the bot

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather (required) |
| `ADMIN_USER_ID` | `0` | Your Telegram user ID (0 = allow all users) |
| `DEFAULT_PINCODE` | `380001` | Default delivery pincode |
| `PRICE_CHECK_INTERVAL_HOURS` | `6` | How often to check prices |
| `SCRAPE_CACHE_TTL_MINUTES` | `30` | Cache duration for scraped data |

## Project Structure

```
bot/
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
├── README.md
├── data/                 # SQLite database (auto-created)
└── src/
    ├── main.py           # Entry point
    ├── config.py         # Settings and product catalog
    ├── bot/
    │   ├── handlers.py   # Telegram command & callback handlers
    │   ├── keyboards.py  # Inline keyboard builders
    │   └── messages.py   # Message templates
    ├── scraper/
    │   ├── amul_scraper.py   # Product price/stock scraper
    │   └── cart_manager.py   # Add-to-cart automation
    ├── scheduler/
    │   └── jobs.py       # Periodic price checks & reminders
    └── db/
        ├── database.py   # SQLite operations
        └── models.py     # Data classes
```

## Troubleshooting

**Bot doesn't respond**: Check that `TELEGRAM_BOT_TOKEN` is correct and the bot is running. Verify `ADMIN_USER_ID` matches your Telegram ID.

**Scraping fails**: shop.amul.com may have changed its layout. The bot falls back to direct product links. Check logs for details.

**Playwright errors**: Run `playwright install chromium` to ensure the browser is installed. On Linux servers, you may also need `playwright install-deps`.

**Price shows as 0**: The website may be using dynamic rendering that the scraper can't parse. Prices will update on the next successful scrape.
