import telebot
from telebot import types
import requests
import time
import random

# --- Configuration ---
# Your provided Telegram bot token
BOT_TOKEN = "7990223109:AAFe3Q6K8mEtECbAeQak29nldkC-o15qq3o"

# --- API URLs ---
# Service 1 (Primary): tempmail.lol
TEMPMAIL_LOL_API = "https://api.tempmail.lol/v2"
# Service 2 (Backup): 1secmail.com
SECMAIL_API = "https://www.1secmail.com/api/v1/"

# --- Bot Initialization ---
# Using threaded=True for better performance and responsiveness
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# A dictionary to save user inbox data (including which service was used)
user_inboxes = {}

# --- Helper function to create the keyboard menu ---
def create_keyboard_menu():
    """Creates the Reply Keyboard with main action buttons."""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🆕 New Email")
    btn2 = types.KeyboardButton("📥 Check Mail")
    btn3 = types.KeyboardButton("🗑️ Delete Email")
    markup.add(btn1, btn2, btn3)
    return markup

# --- Bot Handlers ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handles /start and /help commands, and sets up the main menu."""
    help_text = """
    👋 **Welcome to the Professional Temp Mail Bot!**

    This bot is reliable and uses multiple services to ensure it's always working.

    **You can use the buttons below or the command menu `(/)` to operate the bot.**

    - `/new_email` - Get a new temporary email.
    - `/check_mail` - Check your inbox for new messages.
    - `/delete_email` - Delete your current temporary email.
    """
    bot.reply_to(message, help_text, parse_mode='Markdown', reply_markup=create_keyboard_menu())

@bot.message_handler(commands=['new_email'])
@bot.message_handler(func=lambda message: message.text == "🆕 New Email")
def generate_new_email(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing') # Show "typing..." status instantly
    
    email_address = None
    token = None
    service_used = None

    # --- Try Service 1 (tempmail.lol) ---
    try:
        bot.send_message(chat_id, "⏳ Trying Service 1 (tempmail.lol)...")
        response = requests.post(f"{TEMPMAIL_LOL_API}/inbox/create", timeout=10)
        response.raise_for_status()
        data = response.json()
        email_address = data.get("address")
        token = data.get("token")
        service_used = 'tempmail.lol'
        if not email_address or not token: raise Exception("Invalid response from tempmail.lol")
    except Exception as e:
        print(f"Service 1 failed: {e}")
        bot.send_message(chat_id, "⚠️ Service 1 failed. Trying backup service...")
        
        # --- Try Service 2 (1secmail.com) as a backup ---
        try:
            bot.send_chat_action(chat_id, 'typing')
            response = requests.get(f"{SECMAIL_API}?action=genRandomMailbox&count=1", timeout=10)
            response.raise_for_status()
            email_address = response.json()[0]
            service_used = '1secmail'
        except Exception as e2:
            print(f"Service 2 also failed: {e2}")
            bot.send_message(chat_id, "❌ Both email services seem to be down. Please try again after some time.")
            return

    user_inboxes[chat_id] = {'address': email_address, 'token': token, 'service': service_used}
    reply_text = f"✅ Your new temporary email is ready (from `{service_used}`):\n\n`{email_address}`"
    bot.send_message(chat_id, reply_text, parse_mode='Markdown')

@bot.message_handler(commands=['check_mail'])
@bot.message_handler(func=lambda message: message.text == "📥 Check Mail")
def check_inbox(message):
    chat_id = message.chat.id
    
    if chat_id not in user_inboxes:
        bot.reply_to(message, "🤷 You don't have an active email. Use `/new_email` first.")
        return

    bot.send_chat_action(chat_id, 'typing')
    
    try:
        inbox_data = user_inboxes[chat_id]
        email_address = inbox_data['address']
        service = inbox_data['service']
        
        bot.send_message(chat_id, f"🔍 Checking inbox for `{email_address}`...", parse_mode='Markdown')

        emails = []
        if service == 'tempmail.lol':
            token = inbox_data['token']
            params = {'token': token}
            response = requests.get(f"{TEMPMAIL_LOL_API}/inbox", params=params, timeout=20)
            response.raise_for_status()
            emails = response.json().get('emails', [])
        elif service == '1secmail':
            login, domain = email_address.split('@')
            params = {'action': 'getMessages', 'login': login, 'domain': domain}
            response = requests.get(SECMAIL_API, params=params, timeout=20)
            response.raise_for_status()
            for mail in response.json():
                emails.append({'from': mail['from'], 'subject': mail['subject'], 'body': mail.get('textBody', 'No content')})

        if not emails:
            bot.send_message(chat_id, "⏰ Your inbox is empty.")
            return
            
        latest_email = emails[0]
        mail_from = latest_email.get('from', 'N/A')
        subject = latest_email.get('subject', 'No Subject')
        body = latest_email.get('body', 'No Content')

        if len(body) > 3500: body = body[:3500] + "\n\n[...Message truncated...]"

        reply_text = f"📬 **New Email Received!**\n\n**From:** `{mail_from}`\n**Subject:** `{subject}`\n\n--- **Body** ---\n{body}"
        bot.send_message(chat_id, reply_text, parse_mode='Markdown')

    except Exception as e:
        print(f"Error checking mail: {e}")
        bot.send_message(chat_id, "❌ An error occurred while checking mail. Please try again.")

@bot.message_handler(commands=['delete_email'])
@bot.message_handler(func=lambda message: message.text == "🗑️ Delete Email")
def delete_email(message):
    chat_id = message.chat.id
    if chat_id in user_inboxes:
        del user_inboxes[chat_id]
        bot.reply_to(message, "✅ Your temporary email has been deleted successfully.")
    else:
        bot.reply_to(message, "🤷 You don't have an active email to delete.")

# --- Start The Bot ---
if __name__ == '__main__':
    # This part automatically sets the commands for the menu button
    try:
        bot.set_my_commands([
            telebot.types.BotCommand("/start", "🚀 Start Bot & Get Help"),
            telebot.types.BotCommand("/new_email", "🆕 Create a New Email"),
            telebot.types.BotCommand("/check_mail", "📥 Check Inbox"),
            telebot.types.BotCommand("/delete_email", "🗑️ Delete Current Email"),
        ])
        print("Bot commands updated successfully.")
    except Exception as e:
        print(f"Could not set bot commands: {e}")
    
    print("Professional Temp Mail Bot is running...")
    bot.polling(non_stop=True)