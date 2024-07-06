import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import mysql.connector

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Replace 'YOUR_API_TOKEN' with your actual bot API token
TOKEN = '7064747208:AAGNwY04DS82cT7DPywv4b1wpYA-vBriaPA'

# Initialize the Application
application = Application.builder().token(TOKEN).build()

# Database connection settings
db_user = 'avnadmin'
db_pass = 'AVNS_uEF6bJfuxSZNiWz646W'
db_name = 'defaultdb'

# Establish a database connection
cnx = mysql.connector.connect(
    user=db_user,
    password=db_pass,
    host='mysql-bottele-bottele.d.aivencloud.com',
    port=19333,  # or the port number of your MySQL server
    database=db_name
)
cursor = cnx.cursor()

# Dictionary to store user nicknames
user_nicks = {}

# Dictionary to store user chat IDs
user_chats = {}

# Define a state for the conversation
NICK_STATE = 1

# Define a function to handle the /nick command
# ...

async def handle_nick(update, context):
    user_id = update.effective_user.id
    cursor.execute("SELECT nick FROM users WHERE tele_id = %s", (update.message.chat.id,))
    result = cursor.fetchone()
    if result:
        await update.message.reply_text(f"Nickname mu adalah: {result[0]}")
    else:
        await update.message.reply_text("Kamu tidak memiliki nickname, balas dengan nicknamemu")
    return NICK_STATE

async def handle_nick_message(update, context):
    user_id = update.effective_user.id
    new_nick = update.message.text.strip()  # remove leading and trailing whitespace

    if not new_nick:
        await update.message.reply_text("Nickname cannot be empty!")
        return

    cursor.execute("SELECT nick FROM users WHERE tele_id = %s", (update.message.chat.id,))
    result = cursor.fetchone()
    if result:
        old_nick = result[0]
    else:
        old_nick = None

    # Insert or update the user's nickname in the database
    cursor.execute("INSERT INTO users (tele_id, tele_username, nick, activities) VALUES (%s, %s, %s, 'afk') ON DUPLICATE KEY UPDATE nick = %s", (update.message.chat.id, update.message.chat.username, new_nick, new_nick))
    cnx.commit()

    if old_nick:
        for user_id, chat_id in user_chats.items():
            if chat_id != update.effective_chat.id:
                await context.bot.send_message(chat_id, f"{old_nick} telah merubah nickname menjadi {new_nick}!")
        await update.message.reply_text(f"Nick mu berhasil berubah ke: {new_nick}")
    else:
        await update.message.reply_text(f"Nick mu berhasil di set ke: {new_nick}\nklik /join untuk bergabung")
    return ConversationHandler.END

# Define a function to handle the /join command
async def handle_join(update, context):
    user_id = update.effective_user.id
    cursor.execute("SELECT nick FROM users WHERE tele_id = %s", (update.message.chat.id, ))
    result = cursor.fetchone()
    if result:
        nick = result[0]
    else:
        await update.message.reply_text("Kamu belum memiliki nickname, klik /nick untuk mengatur nickname")
        return  # exit the function if no nick is set

    if user_id not in user_chats:
        chat_id = update.effective_chat.id
        user_chats[user_id] = chat_id
        for user_id_in_group, chat_id_in_group in user_chats.items():
            if chat_id_in_group!= update.effective_chat.id:
                await context.bot.send_message(chat_id_in_group, f"{nick} bergabung ke dalam grup chat!")
        cursor.execute("UPDATE users SET activities = 'online' WHERE tele_id = %s", (update.message.chat.id,))
        cnx.commit()
        await update.message.reply_text(f"Berhasil masuk ke dalam grup chat")

        # Set activity to 'online'
        

    else:
        await update.message.reply_text("Kamu sudah berada di grup chat!")

# Define a function to handle the /leave command
async def handle_leave(update, context):
    user_id = update.effective_user.id
    if user_id in user_chats:
        chat_id = update.effective_chat.id
        del user_chats[user_id]
        nick = user_nicks[user_id]
        for user_id, chat_id_in_group in user_chats.items():
            if chat_id_in_group == chat_id:
                await context.bot.send_message(chat_id_in_group, f"{nick} meninggalkan grup chat!")
        cursor.execute("UPDATE users SET activities = 'afk' WHERE tele_id = %s", (update.message.chat.id, ))
        cnx.commit()
        await update.message.reply_text("Berhasil meninggalkan grup chat!")
    else:
        await update.message.reply_text("kamu tidak di dalam grup chat!")

# Define a function to handle the /list command
async def handle_list(update, context):
    cursor.execute("SELECT nick, activities FROM users")
    results = cursor.fetchall()

    online_nicks = [nick for nick, activity in results if activity == 'online']
    afk_nicks = [nick for nick, activity in results if activity == 'afk']

    online_list = ", ".join(online_nicks) if online_nicks else "None"
    afk_list = ", ".join(afk_nicks) if afk_nicks else "None"

    output = f"Online:\n{online_list}\n\nAFK:\n{afk_list}"
    await update.message.reply_text(output)

# Define a function to handle messages in the group chat
async def handle_group_message(update, context):
    user_id = update.effective_user.id
    if user_id not in user_chats:
        await update.message.reply_text("kamu tidak berada di percakapan klik /join")
        return

    cursor.execute("SELECT nick FROM users WHERE tele_id = %s", (update.message.chat.id, ))
    result = cursor.fetchone()
    nick = result[0]
    chat_id = update.effective_chat.id

    if update.message.text:
        message = update.message.text
        for user_id, chat_id in user_chats.items():
            if chat_id!= update.effective_chat.id:
                await context.bot.send_message(chat_id, f"{nick}: {message}")

    if update.message.photo:
        photo = update.message.photo[-1] 
        caption = f"{nick}:{update.message.caption}" # Get the highest resolution photo
        for user_id, chat_id in user_chats.items():
            if chat_id!= update.effective_chat.id:
                await context.bot.send_photo(chat_id, photo.file_id, caption=caption)


    if update.message.video:
        video = update.message.video
        caption = f"{nick}:{update.message.caption}"  # Add the nickname to the caption
        for user_id, chat_id in user_chats.items():
            if chat_id!= update.effective_chat.id:
                await context.bot.send_video(chat_id, video.file_id, caption=caption)

    if update.message.audio:
        audio = update.message.audio
        for user_id, chat_id in user_chats.items():
            if chat_id!= update.effective_chat.id:
                await context.bot.send_audio(chat_id, audio.file_id)
    
    if update.message.animation:  # Handle GIFs
        animation = update.message.animation
        caption = f"{nick}:{update.message.caption}"  # Add the nickname to the caption
        for user_id, chat_id in user_chats.items():
            if chat_id!= update.effective_chat.id:
                await context.bot.send_animation(chat_id, animation.file_id, caption=caption)
# Define a function to handle the /start command
async def handle_start(update, context):
    await update.message.reply_text("Selamat datang di random group chat,\n"
                                    "\n"
                                    "Buat nicname dulu dengan klik /nick\n"
                                    "Lalu klik /join untuk memasuki group chat\n"
                                    "\n"
                                    "/help -- untuk menampilkan list command")

async def handle_help(update, context):
    await update.message.reply_text("Perintah yang dapat digunakan di bot ini\n"
                                    "\n"
                                    "/join -- masuk kedalam grup chat\n"
                                    "/leave -- keluar dari grup chat\n"
                                    "/nick -- mengatur nickname yang akan ditampilkan\n"
                                    "/help -- untuk menampilkan list command")

# Add a command handler for /start
application.add_handler(CommandHandler('start', handle_start))



# Add a command handler for /nick
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('nick', handle_nick)],
    states={
        NICK_STATE: [MessageHandler(filters.TEXT, handle_nick_message)]
    },
    fallbacks=[]
)

application.add_handler(conv_handler)

# Add a command handler for /join
application.add_handler(CommandHandler('join', handle_join))

# Add a command handler for /list
application.add_handler(CommandHandler('list', handle_list))

application.add_handler(CommandHandler('leave', handle_leave))

application.add_handler(CommandHandler('help', handle_help))

# Add a message handler for the group chat
application.add_handler(MessageHandler(filters.TEXT, handle_group_message))
application.add_handler(MessageHandler(filters.PHOTO, handle_group_message))
application.add_handler(MessageHandler(filters.VIDEO, handle_group_message))
application.add_handler(MessageHandler(filters.AUDIO, handle_group_message))
application.add_handler(MessageHandler(filters.ANIMATION, handle_group_message))
# Start the bot
application.run_polling()