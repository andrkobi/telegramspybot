from telethon import TelegramClient, events
import asyncio
import json
import os
from datetime import datetime
import aiohttp
from keep_alive import keep_alive  # ⬅️ импортируем сервер

# Конфигурация
api_id = 18791166
api_hash = '58e51d1925931a8a05304bf3a16d932d'
OWNER_ID = 5171585034
log_chat_id = -4647191781
tg_password = "march032020"

client = TelegramClient('spy_session', api_id, api_hash)
message_memory = {}

# Безопасное создание папки media_temp
if os.path.exists("media_temp") and not os.path.isdir("media_temp"):
    os.remove("media_temp")

os.makedirs("media_temp", exist_ok=True)

def update_stat(user_id, action):
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        with open('stats.json', 'r') as f:
            stats = json.load(f)
    except:
        stats = {}

    if today not in stats:
        stats[today] = {}

    if str(user_id) not in stats[today]:
        stats[today][str(user_id)] = {"deleted": 0, "edited": 0}

    stats[today][str(user_id)][action] += 1

    with open('stats.json', 'w') as f:
        json.dump(stats, f)

@client.on(events.NewMessage(incoming=True))
async def handle_all(event):
    if event.is_private:
        message_memory[event.message.id] = {
            'text': event.text,
            'sender_id': event.sender_id,
            'message': event.message
        }

        if event.message.ttl_period and event.message.media:
            sender = await event.get_sender()
            file_path = await client.download_media(event.message.media, file=f"media_temp/{event.id}")
            await client.send_message(
                log_chat_id,
                f"📸 Временное медиа от [{sender.first_name}](tg://user?id={sender.id}) сохранено как `{file_path}`",
                parse_mode='md'
            )
            await client.send_file(log_chat_id, file_path)

@client.on(events.MessageDeleted())
async def handler_deleted(event):
    for msg_id in event.deleted_ids:
        data = message_memory.get(msg_id)
        if data:
            sender = await client.get_entity(data['sender_id'])
            text = data['text'] or "<без текста>"
            msg_obj = data['message']
            caption = f"🗑 Удалено сообщение от [{sender.first_name}](tg://user?id={sender.id}):"

            if msg_obj.media:
                await client.send_message(log_chat_id, caption, parse_mode='md')
                await client.send_file(log_chat_id, msg_obj.media, caption=text if text else None)
            else:
                await client.send_message(log_chat_id, f"{caption}\n\n{text}", parse_mode='md')

            update_stat(sender.id, "deleted")

@client.on(events.MessageEdited())
async def handler_edited(event):
    if not event.is_private:
        return
    old = message_memory.get(event.message.id)
    sender = await event.get_sender()
    old_text = old['text'] if old else "<неизвестно>"
    new_text = event.text or "<без текста>"

    await client.send_message(
        log_chat_id,
        f"✏️ Сообщение от [{sender.first_name}](tg://user?id={sender.id}) было изменено:\n\n"
        f"*Старое:* {old_text}\n\n*Новое:* {new_text}",
        parse_mode='md'
    )
    update_stat(sender.id, "edited")
    message_memory[event.message.id] = {
        'text': new_text,
        'sender_id': event.sender_id,
        'message': event.message
    }

@client.on(events.NewMessage(pattern='/s'))
async def command_status(event):
    if event.sender_id == OWNER_ID:
        await event.respond("✅ Бот работает")

@client.on(events.NewMessage(pattern='/r'))
async def command_reload(event):
    if event.sender_id == OWNER_ID:
        await event.respond("♻️ Перезапуск...")
        await client.disconnect()
        exit(1)

@client.on(events.NewMessage(pattern='/off'))
async def command_kill(event):
    if event.sender_id == OWNER_ID:
        await event.respond("💣 Бот отключается.")
        await client.disconnect()
        exit(0)

# ✅ Авто-пинг и сообщение о статусе
async def keep_alive_loop():
    url = "https://480b4ef3-6b33-4a30-b4e5-a6fa6163c378-00-34v3selqfitjr.worf.replit.dev/"
    count = 0
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url):
                    pass
        except:
            pass

        count += 1
        if count >= 10:  # каждые ~30 минут
            try:
                await client.send_message(log_chat_id, "🤖 Бот онлайн и работает.")
            except Exception as e:
                print(f"⚠️ Ошибка при отправке статусного сообщения: {e}")
            count = 0

        await asyncio.sleep(180)  # каждые 3 минуты

# ✅ Запуск
async def main():
    keep_alive()  # ⬅️ запуск Flask-сервера
    await client.start(password=tg_password)
    try:
        await client.send_message(log_chat_id, "🟢 Бот запущен.")
    except Exception as e:
        print(f"⚠️ Не удалось отправить сообщение о запуске: {e}")
    print("✅ Бот запущен.")
    await asyncio.gather(client.run_until_disconnected(), keep_alive_loop())

asyncio.run(main())
