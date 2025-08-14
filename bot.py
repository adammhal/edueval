import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import openai
import aiohttp
from moviepy.editor import VideoFileClip
import asyncio
import json
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

openai.api_key = OPENAI_API_KEY

try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open(GOOGLE_SHEET_NAME)
    worksheet = spreadsheet.sheet1
except Exception as e:
    print(f"Error connecting to Google Sheets: {e}")
    print("Please ensure your credentials path and sheet name are correct and the sheet is shared with the service account.")
    exit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def transcribe_audio(audio_path):
    with open(audio_path, "rb") as audio_file:
        transcription = await asyncio.to_thread(
            openai.Audio.transcribe, "whisper-1", audio_file
        )
    return transcription['text']

async def get_structured_evaluation(transcript):
    system_prompt = """
    You are an expert evaluator of teaching skills named EduEval.
    Your task is to analyze the provided transcript from a teacher applicant's video.
    Based on the transcript, evaluate the applicant on the following criteria on a scale of 1-5:
    1. Clarity: How clear and concise was the communication?
    2. Pacing: Was the delivery well-paced?
    3. Engagement: How engaging was the teacher?
    4. Mastery: How well did the teacher demonstrate subject matter expertise?

    Your response MUST be a valid JSON object with the following structure:
    {
      "clarity_rating": <integer>,
      "pacing_rating": <integer>,
      "engagement_rating": <integer>,
      "mastery_rating": <integer>,
      "summary": "<string: A brief summary of your findings>",
      "recommendation": "<string: 'Recommend for Interview' or 'Do Not Recommend'>"
    }
    Do not include any text outside of the JSON object.
    """
    
    response = await asyncio.to_thread(
        openai.ChatCompletion.create,
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please evaluate the following transcript:\n\n{transcript}"}
        ],
        temperature=0.5
    )
    return response.choices[0].message['content']

def append_to_sheet(data):
    try:
        row = [
            data.get('name'),
            data.get('email'),
            data.get('discord_id'),
            data.get('clarity_rating'),
            data.get('pacing_rating'),
            data.get('engagement_rating'),
            data.get('mastery_rating'),
            data.get('summary'),
            data.get('recommendation'),
            data.get('video_link')
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        print(f"Failed to append row to Google Sheet: {e}")
        return False

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print('EduEval is ready and connected to Google Sheets.')

@bot.command(name='evaluate')
async def evaluate(ctx, name: str, email: str):
    if not ctx.message.attachments:
        await ctx.send("Please attach a video file to evaluate.")
        return

    attachment = ctx.message.attachments[0]
    if not attachment.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
        await ctx.send("Unsupported file type. Please upload a valid video file.")
        return

    video_path = f"./{attachment.filename}"
    audio_path = f"./{os.path.splitext(attachment.filename)[0]}.mp3"

    try:
        await ctx.send(f"Processing `{attachment.filename}` for **{name}**... This may take a few minutes.")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    with open(video_path, 'wb') as f:
                        f.write(await resp.read())

        await ctx.send("Extracting audio...")
        video_clip = VideoFileClip(video_path)
        await asyncio.to_thread(video_clip.audio.write_audiofile, audio_path)
        video_clip.close()
        
        await ctx.send("Transcribing audio...")
        transcript = await transcribe_audio(audio_path)
        
        await ctx.send("Analyzing transcript with GPT-4...")
        evaluation_json_str = await get_structured_evaluation(transcript)
        evaluation_data = json.loads(evaluation_json_str)

        sheet_data = {
            "name": name,
            "email": email,
            "discord_id": str(ctx.author.id),
            "video_link": attachment.url,
            **evaluation_data
        }

        await ctx.send("Logging results to Google Sheets...")
        success = await asyncio.to_thread(append_to_sheet, sheet_data)

        if success:
            await ctx.send(f"Evaluation for **{name}** complete and logged successfully!")
            summary_message = (
                f"**Summary:** {evaluation_data['summary']}\n"
                f"**Recommendation:** {evaluation_data['recommendation']}"
            )
            await ctx.send(summary_message)
        else:
            await ctx.send("Failed to log results to Google Sheets. Please check the bot's console for errors.")

    except json.JSONDecodeError:
        await ctx.send("Error: The AI returned an invalid format. Please try again.")
    except Exception as e:
        await ctx.send(f"An unexpected error occurred: {e}")
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)

bot.run(DISCORD_TOKEN)
