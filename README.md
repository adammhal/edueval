# EduEval Discord Bot

EduEval is a Python-based Discord bot designed to automate the initial screening process for teacher applicants. It uses AI to analyze video submissions and provides a structured evaluation, which is then logged to a Google Sheet.

## Features

* **Video Submission:** Accepts video file submissions (`.mp4`, `.mov`, etc.) directly in a Discord channel through a `!evaluate` command.
* **Audio Transcription:** Automatically extracts the audio from the submitted video and transcribes it into text using OpenAI's Whisper API.
* **AI-Powered Evaluation:** Sends the transcript to GPT-4 for a detailed analysis based on predefined teaching criteria (Clarity, Pacing, Engagement, and Mastery).
* **Structured Data Output:** The AI returns a structured JSON object containing numerical ratings for each category, a written summary, and a final recommendation.
* **Google Sheets Integration:** Automatically logs all relevant applicant information—including their name, email, Discord ID, video link, and the complete AI evaluation—into a new row in a designated Google Sheet.
* **Discord Feedback:** Confirms the successful evaluation and logging process directly in the Discord channel and provides a brief summary of the AI's findings.
