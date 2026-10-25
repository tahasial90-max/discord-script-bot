import discord
from discord.ext import commands
import requests
import io
from PIL import Image
from google import genai
import os

# Bot-Einrichtung
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Gemini AI für die Texterkennung im Bild (sicher über Umgebungsvariable)
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@bot.event
async def on_ready():
    print(f"Bot ist bereit als {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Prüfen, ob du ein Bild an den Bot geschickt hast
    if message.attachments:
        attachment = message.attachments[0]
        if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
            status_msg = await message.reply("🔍 *Lese Skript aus dem Bild und erstelle Pastefy-Link...*")
            
            try:
                # Bild herunterladen
                image_bytes = await attachment.read()
                image = Image.open(io.BytesIO(image_bytes))

                # Text aus dem Bild extrahieren lassen
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[image, "Extrahiere nur den reinen Lua/Luau Code aus diesem Bild. Gib absolut keinen anderen Text, keine Erklärungen und keine Markdown-Codeblocks (wie ```lua) zurück."]
                )
                
                extracted_code = response.text.strip()
                
                # Falls doch Markdown-Zeichen da sind, entfernen
                if extracted_code.startswith("```"):
                    extracted_code = "\n".join(extracted_code.split("\n")[1:-1])

                if not extracted_code:
                    await status_msg.edit(content="❌ Konnte keinen Code auf dem Bild erkennen.")
                    return

                # Automatischer Upload zu Pastefy
                paste_data = {
                    "type": "PASTE",
                    "title": "Roblox Script",
                    "content": extracted_code
                }
                
                res = requests.post("https://api.pastefy.app/v1/paste", json=paste_data)
                
                if res.status_code in [200, 201]:
                    paste_id = res.json().get("paste", {}).get("id")
                    raw_url = f"https://pastefy.app/{paste_id}/raw"
                    
                    # Fertigen loadstring-Befehl ausgeben
                    executor_command = f'loadstring(game:HttpGet("{raw_url}"))()'
                    
                    await status_msg.edit(
                        content=f"✅ **Erfolgreich umgewandelt!**\n\n"
                                f"Füge das in deinen Executor ein:\n"
                                f"```lua\n{executor_command}\n```"
                    )
                else:
                    await status_msg.edit(content="❌ Fehler beim Hochladen auf Pastefy.")

            except Exception as e:
                await status_msg.edit(content=f"❌ Fehler bei der Verarbeitung: {e}")

    await bot.process_commands(message)

# Bot starten über die sichere Umgebungsvariable
bot.run(os.environ.get("DISCORD_TOKEN"))
