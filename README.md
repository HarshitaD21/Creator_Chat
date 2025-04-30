# Creator_Chat
An automated system using Gemini AI and Streamlit 
It is coversational chatbot used to generate, tag, and schedule media content for YouTube uploads, automating up to 10 uploads/day. 
Integrated third-party APIs for trending content, structured data handling, and OAuth-based publishing, reducing manual processing time by 60% and enabling scalable, cross-platform automation for content delivery.
# 🎬 Gemini + Streamlit Creator Bot

This AI-powered Streamlit app uses Google Gemini to help creators **edit, schedule, and auto-upload videos** with smart metadata extraction, content suggestions, and more. Ideal for YouTube and future multi-platform automation.

## 🚀 Features

- ✂️ Trim and edit videos from chat prompts
- 🧠 Gemini-powered title, description, and tag suggestions
-  📊 See trending videos and keyword insights
- 📅 Schedule YouTube uploads with local time input


## 🛠 Tech Stack

- `Google Gemini API` (text + metadata extraction)
- 🎞️ Streamlit – chat UI and app frontend
- `Python` (core logic and APIs)
- `YouTube Data API v3` (upload + schedule)
- `pytube`, `moviepy` (video processing)
- 📽️ FFmpeg – for video editing and trimming
- 🧩 Other APIs – GIF libraries, localization, trend fetching

### 📂 Project Structure

<pre> ```plaintext Creator_Chat/ ├── app.py # Main Streamlit app with Gemini-powered chatbot ├── youtube_uploader.py # Handles YouTube authentication, uploads, scheduling, and metadata ├── utils.py # Helper functions (if applicable) ├── client_secret.json # OAuth credentials for YouTube API (DO NOT COMMIT) ├── requirements.txt # Python dependencies ├── .env # Environment config for Gemini & paths └── README.md # Project documentation ``` </pre>


### 🔑 YouTube API Setup

To enable YouTube upload and scheduling features, you must:

1. **Create a Google Cloud Project**
   - Go to: [Google Cloud Console](https://console.cloud.google.com/)
   - Click "New Project" and give it a name.

2. **Enable YouTube Data API v3**
   - In the left sidebar, go to **APIs & Services > Library**
   - Search for **YouTube Data API v3**
   - Click **Enable**

3. **Create OAuth 2.0 Credentials**
   - Go to **APIs & Services > Credentials**
   - Click **"Create Credentials" > OAuth client ID**
   - Select:
     - **Application type**: Desktop App or Web App
     - Provide any name
   - Download the `client_secret.json` file and place it in the root of this project

4. **Add the following line to your `.env` file**
```dotenv
GOOGLE_CLIENT_SECRET_FILE=client_secret.json


Steps to run the app on your local system
1. Clone the repo :
git clone https://github.com/HarshitaD21/Creator_Chat.git
cd Creator_Chat

2. Install dependencies: 
pip install -r requirements.txt

3. Set up environment:
Create a .env file conatining 
API_KEY=your_gemini_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here

4.Place your youtube API credentials 
Download client_secret.json from the Google Cloud Console and place it in the project root.

5. Run the app
streamlit run app.py



🌱 Future Improvements
Improve Gemini’s contextual awareness for multi-turn conversations
Enable Instagram and TikTok upload automation
Add multi-language voice command support
Real-time YouTube analytics dashboard + sentiment detection


