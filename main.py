import os
import json
import ccxt
import pandas as pd
import mplfinance as mpf
from io import BytesIO
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SYMBOLS_FILE = 'symbols.json'

def load_symbols():
    try:
        with open(SYMBOLS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_symbols(symbols):
    with open(SYMBOLS_FILE, 'w') as f:
        json.dump(symbols, f)

def job(bot: Bot):
    print("🟡 Запуск задачи job()...")
    symbols = load_symbols()
    if not symbols:
        print("⚠️ Нет монет в списке.")
        return

    exchange = ccxt.bitget()
    for symbol in symbols:
        print(f"🔍 Обрабатываю {symbol}")
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=40)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            buf = BytesIO()
            mpf.plot(df, type='candle', style='charles', volume=True, savefig=buf)
            buf.seek(0)

            print(f"📤 Отправка графика по {symbol}")
            bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=buf, caption=f"📈 {symbol} (15m)")
            print(f"✅ Успешно отправлено: {symbol}")
        except Exception as e:
            print(f"❌ Ошибка при {symbol}: {e}")

def add(update: Update, context):
    if len(context.args) != 1:
        update.message.reply_text("Используй: /add SYMBOL/USDT")
        return
    symbol = context.args[0].upper()
    symbols = load_symbols()
    if symbol not in symbols:
        symbols.append(symbol)
        save_symbols(symbols)
        update.message.reply_text(f"✅ Добавлено: {symbol}")
    else:
        update.message.reply_text("⛔ Уже есть в списке.")

def remove(update: Update, context):
    if len(context.args) != 1:
        update.message.reply_text("Используй: /remove SYMBOL/USDT")
        return
    symbol = context.args[0].upper()
    symbols = load_symbols()
    if symbol in symbols:
        symbols.remove(symbol)
        save_symbols(symbols)
        update.message.reply_text(f"🗑 Удалено: {symbol}")
    else:
        update.message.reply_text("⛔ Нет такой пары.")

def list_symbols(update: Update, context):
    symbols = load_symbols()
    if symbols:
        update.message.reply_text("📊 Монеты в отслеживании:\n" + "\n".join(symbols))
    else:
        update.message.reply_text("Список пуст.")

def main():
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("add", add))
    dispatcher.add_handler(CommandHandler("remove", remove))
    dispatcher.add_handler(CommandHandler("list", list_symbols))

    updater.start_polling()
    print("🤖 Бот запущен.")

    print("🔧 Пробная отправка графика вручную...")
    job(updater.bot)

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: job(updater.bot), trigger='cron', minute='*/15')
    scheduler.start()
    print("⏰ Планировщик работает.")

    updater.idle()

if __name__ == "__main__":
    main()