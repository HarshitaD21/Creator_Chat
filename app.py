import streamlit as st
import google.generativeai as genai
import dotenv
import requests
from io import BytesIO
import base64
from youtube_uploader import upload_video, get_authenticated_service
import imageio
from PIL import Image
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip
import tempfile
import requests
from moviepy.editor import *
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
import re   
import yt_dlp
import whisper
import json
import tempfile
import os
import json
import pickle
import dotenv
from datetime import date, timedelta, datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import plotly.express as px
import pandas as pd
from youtube_uploader import upload_video  # ensure this file includes upload logic
import streamlit as st
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload



# Load environment variables
dotenv.load_dotenv()
api_key = os.getenv("API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
tenor_api_key = os.getenv("TENOR_API_KEY")
CLIENT_SECRETS  = "client_secret.json"
TOKEN_FILE      = "token.pickle"
custom_temp_dir = os.path.join(os.getcwd(), "temp_videos")
os.makedirs(custom_temp_dir, exist_ok=True)  # creates if doesn't exist

# ─── Auth ───
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",  # Read access to YouTube content
    "https://www.googleapis.com/auth/youtube.force-ssl",  # For uploading videos
    "https://www.googleapis.com/auth/yt-analytics.readonly"  # Access to YouTube Analytics
]

genai.configure(api_key=api_key)

# Initialize Gemini model
model = genai.GenerativeModel("gemini-2.0-flash")

st.set_page_config(layout="wide")
# st.markdown("<h1 style='text-align: center;'>🎥 My Creator Bot</h1>", unsafe_allow_html=True)

main_col, chat_col = st.columns([2, 1], gap="large")

# ========================
# Initialize Session State
# ========================
def initialize_state():
    defaults = {
        "edited_video_path": None,
        "prompt_history": [],
        "clear_flag": False,
        "btn_clicked": False,
        "gifs_to_insert": [],
        "chat_history": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_state()
# Custom directory for temporary files
# custom_temp_dir = os.path.join(os.getcwd(), "temp_files")

# # Ensure the directory exists
# if not os.path.exists(custom_temp_dir):
#     os.makedirs(custom_temp_dir)

def get_authenticated_service():
    creds = None
    # Check if the token file exists
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # If no valid credentials, prompt the user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.ressfresh_token:
            creds.refresh(Request())
        else:
            # Run the OAuth flow to get new credentials
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for next time
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    # Build and return the YouTube API services
    return build("youtubeAnalytics", "v2", credentials=creds), build("youtube", "v3", credentials=creds)

# Modify the get_trending_videos to use authenticated API call
def get_trending_videos(region="US", max_results=5):
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)  # Initialize with the API key
        res = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode=region,
            maxResults=max_results
        ).execute()

        trending_videos = [{
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "views": item["statistics"].get("viewCount", "N/A"),
            "videoId": item["id"],
            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"]
        } for item in res.get("items", [])]

        if not trending_videos:
            raise ValueError("No trending videos found")

        return trending_videos

    except Exception as e:
        return f"❌ Error fetching trending videos: {str(e)}"

# Authenticate with YouTube
def youtube_authenticate():
    API_NAME = 'youtube'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS, SCOPES)
    credentials = flow.run_local_server(port = 0)
    
    youtube = googleapiclient.discovery.build(API_NAME, API_VERSION, credentials=credentials)
    return youtube

# Auto-reply to comments
def auto_reply_to_comments(youtube, video_id, reply_text="Thanks for your comment!"):
    st.write(f"📹 Fetching comments for Video ID: {video_id}")
    
    request = youtube.commentThreads().list(
        part='snippet',
        videoId=video_id,
        textFormat='plainText'
    )
    
    try:
        response = request.execute()
        
        # Debugging: Log the response directly
        # st.write("Raw comment response:", response)

        if 'items' in response and response['items']:
            for item in response['items']:
                comment_id = item['id']
                author = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
                comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                
                # Log the comment details
                st.write(f"💬 {author} commented: {comment}")
                # st.info(f"Sending auto-reply to {author}")

                reply_request = youtube.comments().insert(
                    part='snippet',
                    body={
                        'snippet': {
                            'parentId': comment_id,
                            'textOriginal': reply_text
                        }
                    }
                )
                reply_response = reply_request.execute()

                # Log the reply response
                # st.write(f"Reply Response: {reply_response}")
                st.success(f"✅ Replied to {author}")

        else:
            st.write("No comments found for this video.")
            
    except googleapiclient.errors.HttpError as e:
        st.error(f"Error fetching comments or replying: {e}")

def analyze_video_with_gemini_vision(video_path):
    with open(video_path, "rb") as video_file:
        video_data = video_file.read()
    
    vision_model = genai.GenerativeModel("gemini-pro-vision")  # or another vision-capable model
    response = vision_model.generate_content(video_data)
    return response.text


def transcribe_audio(video_path):
    model = whisper.load_model("base")
    audio = VideoFileClip(video_path).audio
    temp_audio_path = "temp_audio.wav"
    audio.write_audiofile(temp_audio_path)
    result = model.transcribe(temp_audio_path)
    return result["text"]

def repurpose_video_or_audio_for_reel(content_type, input_content, video_path=None, audio_path=None):
    if content_type == "Reel":
        if video_path:
            # Add logic to handle video-based content (like trimming or summarizing video)
            return generate_reel_from_video(video_path, input_content)
        elif audio_path:
            # Handle audio-based content (e.g., create a short audio clip or summarize)
            return generate_reel_from_audio(audio_path, input_content)
    else:
        return input_content  # If it's not a "Reel", return the original content

# Function to generate short-form content for Twitter (Tweet)
def generate_tweet_content(input_content):
    # Logic to condense the content to fit Twitter's 280-character limit
    return input_content[:280]

# Function to generate short-form content for a reel (video)
def generate_reel_from_video(video_path, input_content):
    # Logic to create a short video from the given video file (e.g., trimming or selecting segments)
    return f"Reel generated from video at {video_path} with content: {input_content}"

# Function to generate short-form content from audio
def generate_reel_from_audio(audio_path, input_content):
    # Logic to create a short audio clip for a reel or summarize the audio
    return f"Reel generated from audio at {audio_path} with content: {input_content}"


def parse_command(command):
    command = command.lower()

    if "song" in command:
        match = re.search(r"(search|play|add).*?song\s*['\"]?(.+?)['\"]?\s*(?:by\s+([^\s]+))?.*?(?:at|insert\s*at)?\s*(\d+)\s*seconds?", command, re.I)
        if match:
            song = match.group(2)
            artist = match.group(3) or ""
            time = int(match.group(4))
            return {"action": "song", "start": time, "song_artist": f"{song} {artist}".strip()}
        return None, None

    if "trim from" in command:
        match = re.findall(r"trim from (\d+)[s]* to (\d+)[s]*", command)
        if match:
            return {"action": "trim", "start": int(match[0][0]), "end": int(match[0][1])}

    if "add filter" in command:
        if "black and white" in command:
            return {"action": "filter", "type": "bw"}
        if "invert" in command:
            return {"action": "filter", "type": "invert"}

    if "add transition" in command:
        match = re.findall(r"transition at (\d+)[s]*", command)
        if match:
            return {"action": "transition", "at": int(match[0])}

    if "insert gif at" in command:
        match = re.findall(r"gif .* at (\d+)[s]*", command)
        gif_url = re.findall(r"gif of (.*?) at", command)
        if match and gif_url:
            return {"action": "insert_gif", "timestamp": int(match[0]), "gif_desc": gif_url[0]}

    if "translate" in command and "subtitles" in command:
        lang = re.findall(r"translate .* to (\w+)", command)
        if lang:
            return {"action": "translate_subtitle", "language": lang[0]}

    if "stitch" in command:
        return {"action": "stitch", "file": "path_to_other_video.mp4"}  # You can customize this

    return {"action": "unknown"}

def download_audio_from_youtube(query, save_as="song.mp3"):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': False,  # Set to True later, but False helps you debug
        'outtmpl': save_as,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch1:{query}"])
        if not os.path.exists(save_as):
            print("⚠️ Download failed: file not found.")
            return None
        return save_as
    except Exception as e:
        print(f"⚠️ yt_dlp failed: {e}")
        return None

def add_audio_to_video(video, audio_path, start_time):
    audio_clip = AudioFileClip(audio_path).set_start(start_time)
    combined_audio = CompositeAudioClip([video.audio, audio_clip])
    return video.set_audio(combined_audio)

def handle_command(video_path, command):
    video = VideoFileClip(video_path)
    parsed = parse_command(command)

    if parsed["action"] == "trim":
        video = apply_trim(video, parsed["start"], parsed["end"])
    # elif parsed["action"] == "filter":
    #     video = apply_filter(video, parsed["type"])
    elif parsed["action"] == "transition":
        video = apply_transition_at(video, parsed["at"])
    elif parsed["action"] == "insert_gif":
        video = insert_gif_at_timestamp(video, gif_url, parsed["timestamp"], output_path)
    elif parsed["action"] == "translate_subtitle":
        video = apply_translation_and_subtitles(video, parsed["language"])
    elif parsed["action"] == "stitch":
        video = apply_stitch(video, parsed["file"])
    # elif parsed["action"] == "song":
    #     video = apply_song(video, parsed["song_artist"], parsed["start"])
    else:
        print("Unknown command")

    output = "edited_output.mp4"
    video.write_videofile(output, codec="libx264", audio_codec="aac")
    return output

def apply_song(video, song_query, time):
    audio_path = download_audio_from_youtube(song_query, "song.mp3")
    if not audio_path:
        print("❌ Could not download song.")
        return video  # return original unchanged video
    return add_audio_to_video(video, audio_path, time)

def apply_trim(video_path, start, end):
    video = VideoFileClip(video_path).subclip(start, end)
    video = video.set_audio(video.audio)

    # with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_output:
    #     output_path = tmp_output.name

    output_path = os.path.join(custom_temp_dir, "edited_video.mp4")

    video.write_videofile(output_path, codec="libx264", audio_codec="aac")
    video.close()
    return output_path



# def apply_filter(video, type_):
#     if type_ == "bw":
#         return video.fx(vfx.blackwhite).set_audio(video.audio)
#     elif type_ == "invert":
#         return video.fx(vfx.invert_colors).set_audio(video.audio)
#     return video.set_audio(video.audio)
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# --- Fetch Scheduled Videos ---
def list_scheduled_uploads():
    youtube = get_authenticated_service()
    request = youtube.videos().list(
        part="snippet,status",
        mine=True,
        maxResults=10
    )
    response = request.execute()
    scheduled = []
    for item in response.get("items", []):
        status = item["status"].get("privacyStatus")
        if status == "private" and "publishAt" in item["status"]:
            scheduled.append({
                "title": item["snippet"]["title"],
                "publish_time": item["status"]["publishAt"]
            })
    return scheduled



def apply_transition_at(video, timestamp, fade_duration=1):
    part1 = video.subclip(0, timestamp).fx(vfx.fadeout, fade_duration)
    part2 = video.subclip(timestamp).fx(vfx.fadein, fade_duration)
    
    part1 = part1.set_audio(part1.audio)
    part2 = part2.set_audio(part2.audio)

    final = concatenate_videoclips([part1, part2])
    return final.set_audio(final.audio)


def apply_gif(video, gif_url, timestamp):
    gif_path = download_gif(gif_url)
    gif_clip = VideoFileClip(gif_path).resize(video.size).set_audio(None)

    before = video.subclip(0, timestamp)
    after = video.subclip(timestamp)

    # Make sure to set audio for before + after then concatenate
    final = concatenate_videoclips([
        before.set_audio(before.audio),
        gif_clip,
        after.set_audio(after.audio)
    ])

    return final.set_audio(final.audio)


# def apply_stitch(video1, video2_path):
#     video2 = VideoFileClip(video2_path)
#     stitched = concatenate_videoclips([
#         video1.set_audio(video1.audio),
#         video2.set_audio(video2.audio)
#     ])
#     return stitched.set_audio(stitched.audio)

def apply_stitch(video_files, output_file):
    clips = []
    for video in video_files:
        clip = VideoFileClip(video).fadein(1).fadeout(1)  # Apply fade-in and fade-out
        clips.append(clip)

    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip.write_videofile(output_file, codec="libx264", audio_codec="aac")


def apply_translation_and_subtitles(video, language):
    # This would eventually overlay subtitles.
    print(f"Translating to {language} and adding subtitles...")
    return video.set_audio(video.audio)



def timestamp_to_seconds(timestamp):
    parts = timestamp.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

def download_gif(gif_url):
    response = requests.get(gif_url)
    gif_path = 'temp.gif'
    with open(gif_path, 'wb') as f:
        f.write(response.content)
    return gif_path

def insert_gif_at_timestamp(video_path, gif_url, timestamp, output_path):
    original_video = VideoFileClip(video_path)
    gif_path = download_gif(gif_url)

    gif_clip = VideoFileClip(gif_path).set_start(0)
    gif_clip = gif_clip.set_duration(gif_clip.duration).resize(original_video.size)

    # Split video
    before_clip = original_video.subclip(0, timestamp)
    after_clip = original_video.subclip(timestamp)

    # Combine them
    final = concatenate_videoclips([before_clip, gif_clip, after_clip])
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    return output_path

def get_search_terms_from_prompt(user_prompt):
    prompt = f"""
    User wants a GIF. Extract 3 short search keywords or phrases from their request that will help find a matching GIF.
    Request: "{user_prompt}"
    Respond with a comma-separated list only.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def search_gifs(keywords):
    query = keywords.replace(",", "+")
    url = f"https://tenor.googleapis.com/v2/search?q={query}&key={tenor_api_key}&limit=10"
    res = requests.get(url)
    return res.json().get("results", [])

def get_first_frame_from_gif_url(gif_url):
    response = requests.get(gif_url)
    gif_bytes = BytesIO(response.content)
    gif = imageio.mimread(gif_bytes, format="gif")
    first_frame = Image.fromarray(gif[0])
    buffer = BytesIO()
    first_frame.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()

def is_gif_relevant(gif_url, user_prompt):
    frame_b64 = get_first_frame_from_gif_url(gif_url)
    prompt = f"""
    You are an AI that checks if an image matches a user's prompt.
    User prompt: "{user_prompt}"
    Does the image match this request visually? Answer only YES or NO.
    """
    image_data = {"mime_type": "image/jpeg", "data": frame_b64}
    response = model.generate_content([prompt, image_data])
    return response.text.strip().lower() == "yes"

def parse_song_prompt(prompt):
    match = re.search(r"(search|play|add).*?song\s*['\"]?(.+?)['\"]?\s*(?:by\s+([^\s]+))?.*?(?:at|insert\s*at)?\s*(\d+)\s*seconds?", prompt, re.I)
    if match:
        song = match.group(2)
        artist = match.group(3) or ""
        time = int(match.group(4))
        return f"{song} {artist}".strip(), time
    return None, None

def download_audio_from_youtube(query, save_as="song.mp3"):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'outtmpl': save_as,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"ytsearch1:{query}"])
    return save_as

st.markdown(
    """
    <style>
    video {
        width: 700px !important;
        height: 400px !important;
        object-fit: cover;
    }
    html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #a1c4fd, #c2e9fb);
        background-attachment: fixed;
    }
  
    .stButton button {
        background-color: #4CAF50;
        color: white;
        border-radius: 10px;
        padding: 12px 24px;
        font-size: 16px;
        border: none;
        transition: background-color 0.3s ease;
    }
    .stButton button:hover {
        background-color: #45a049;
    }
    .stTextInput input {
        padding: 12px;
        border-radius: 5px;
        border: 1px solid #ddd;
        font-size: 16px;
    }
    .stTextArea textarea {
        padding: 12px;
        border-radius: 5px;
        border: 1px solid #ddd;
        font-size: 16px;
    }
    .stSelectbox select {
        background-color: #fff;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 12px;
        font-size: 16px;
    }
    .stMarkdown {
        text-align: center;
        color: #333;
    }
    .stContainer {
        margin-top: 20px;
    }
    /* Custom styling for the file uploader */
    .file-uploader-container {
        background-color: #eaf1e7;
        border-radius: 8px;
        border: 2px dashed #4CAF50;
        padding: 20px;
        text-align: center;
        cursor: pointer;
        transition: background-color 0.3s ease, border-color 0.3s ease;
    }
    .file-uploader-container:hover {
        background-color: #d4e9d3;
        border-color: #45a049;
    }
    .file-uploader-container p {
        color: #4CAF50;
        font-size: 18px;
        margin-top: 0;
    }
    .video-container {
        margin-top: 30px;
        text-align: center;
    }
    .download-button {
        background-color: #007bff;
        color: white;
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 16px;
        border: none;
        width: 50% !important;  /* Set the uploader width to 50% */
        margin-left: 0;         /* Center the uploader */
    }
    .download-button:hover {
        background-color: #0056b3;
    }
    .stFileUploader {
        width: 50% !important;  /* Set the uploader width to 50% */
        margin-left: 0;         /* Center the uploader */
    }

    

    </style>
    """,
    unsafe_allow_html=True
)


video_placeholder = st.empty()

# --- MAIN PANEL ---
with main_col:
    # Heading
    # st.subheader("🎬 Video Creation Panel")

    # File upload section
    uploaded_file = st.file_uploader(
        "📤 Upload your video (MP4, MOV, AVI only)", 
        type=["mp4", "mov", "avi"],
        label_visibility="collapsed"
        # accept_multiple_files=True
    )
    
    # If a file is uploaded, save it temporarily
    if uploaded_file and not st.session_state.edited_video_path:
        # with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_input:
        #     tmp_input.write(uploaded_file.read())
        uploaded_filename = uploaded_file.name if uploaded_file else "uploaded_video.mp4"
        uploaded_path = os.path.join(custom_temp_dir, uploaded_filename)

        # Save uploaded file to that path
        with open(uploaded_path, "wb") as f:
            f.write(uploaded_file.read())
        st.session_state.edited_video_path = uploaded_path
    
    # Video display section
    if st.session_state.edited_video_path:
        st.markdown("<div class='video-container'>", unsafe_allow_html=True)
        video_placeholder = st.video(st.session_state.edited_video_path)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Download button for the edited video
        with open(st.session_state.edited_video_path, "rb") as f:
            st.download_button(
                label="📥 Download Edited Video", 
                data=f, 
                file_name="final_edited_video.mp4", 
                key="download_video",
                use_container_width=False,
                help="Download the edited video"
            )


# --- CHATBOT PANEL ---
with chat_col:
    st.subheader("💬 Chat")


    # Chat input form
    # with st.form("chat_form", clear_on_submit=True):
    #     user_input = st.text_input("Type your message:")
    #     submitted = st.form_submit_button("Send")
    user_input = st.chat_input("You: ")


    if user_input:
        st.session_state.chat_history.append(("user", user_input))

        prompt = f"""
        You are a video editing assistant. The user says: "{user_input}". 
        Identify their intent and parameters and reply with JSON:
       {{
            "action": "...", 
            "start": 0, 
            "end": 0, 
            "gif_desc": "", 
            "region": "", 
            "max_results": 5,
            "title": "...",
            "description": "...",
            "tags": ["tag1", "tag2"],
            "privacy": "public" | "unlisted" | "private",
            "publish_at": "2025-04-30T10:30:00Z"
            "video_id": "",
            "reply_text": ""
        }}

        Where action is one of ["trim","insert_gif", "upload", "get_trending", "upload" , "schedule" , "analytics", "auto_reply"]. 
        """
        resp = model.generate_content(prompt)
        response_text = resp.candidates[0].content.parts[0].text
        cleaned_response = response_text.strip("```json\n").strip("\n```")

        # try:
        #     parsed = json.loads(resp.text)
        # except json.JSONDecodeError:
        #     parsed = {"action":"unknown"}


        try:    
            parsed = json.loads(cleaned_response)
            print(parsed)

            # Auto GIF insertion logic
            if parsed["action"] == "insert_gif" and st.session_state.edited_video_path:
                st.info("🎯 Detected GIF insertion command. Processing...")
                # Use Gemini to convert prompt to search terms
                gifs = search_gifs(parsed.get('gif_desc'))

                found = False
                for gif in gifs:
                    gif_url = gif["media_formats"]["gif"]["url"]
                    if is_gif_relevant(gif_url, user_input):
                        # with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_output:
                        #     output_path = tmp_output.name
                        output_path = os.path.join(custom_temp_dir, f"edited_{parsed.get('start', 0)}.mp4")

                        st.session_state.edited_video_path = insert_gif_at_timestamp(
                            st.session_state.edited_video_path,
                            gif_url,
                            parsed.get('start'),
                            output_path
                        )
                        bot_reply = f"✅ Inserted a relevant GIF at {parsed.get('start')} seconds."
                        found = True
                        video_placeholder.video(st.session_state.edited_video_path)
                        break

                if not found:
                    bot_reply = "😔 No relevant GIF found for your request."

            elif parsed["action"] == "trim" and st.session_state.edited_video_path:
            
                st.info("✂️ Trimming video...")

                trimmed_path = apply_trim(
                    st.session_state.edited_video_path,
                    parsed.get("start"),
                    parsed.get("end")
                )

                st.session_state.edited_video_path = trimmed_path
                video_placeholder.video(trimmed_path)

                bot_reply = f"✅ Trimmed video from {parsed.get('start')}s to {parsed.get('end')}s."
            elif parsed["action"] == "auto_reply":
                video_id = parsed.get("video_id")
                reply_text = parsed.get("reply_text")
                bot_reply =  "🔐 Authenticating with YouTube..."
                youtube = youtube_authenticate()
                auto_reply_to_comments(youtube, video_id, reply_text)
                bot_reply = "✅ Auto-replies sent!"
            elif parsed["action"] == "get_tre`nding":
                region = parsed.get("region", "US")
                # ["US", "IN", "GB", "JP", "CA"]
                region = parsed.get("region", "US")
                max_results = parsed.get("max_results", 5)
                trending_videos = get_trending_videos(region=region, max_results=max_results)
                print(trending_videos)
                if isinstance(trending_videos, str) and trending_videos.startswith("❌"):
                    bot_reply = "error fetching trending videos"
                else:
                    bot_reply = f"📺 Trending videos in {region}:\n"
                    for video in trending_videos:
                        bot_reply += f"\n**{video['title']}**\n"
                        bot_reply += f"Channel: {video['channel']}, Views: {video['views']}\n"
                        bot_reply += f"[Watch](https://www.youtube.com/watch?v={video['videoId']})\n"

                    st.session_state.trending_videos = trending_videos  # Store if needed

            elif parsed["action"] == "upload" and st.session_state.edited_video_path:
                bot_reply = f"✅ Uploading youtube video."
                video_id = upload_video(
                st.session_state.edited_video_path,
                parsed["title"],
                parsed["description"],
                parsed.get("tags", []),
                parsed["privacy"]
                )
                bot_reply = f"✅ Uploaded! Video ID: {video_id}"
            elif parsed["action"] == "schedule":
                iso_time = parsed["publish_at"]
                video_id = upload_video(
                    st.session_state.edited_video_path,
                    parsed["title"],
                    parsed["description"],
                    parsed.get("tags", []),
                    parsed["privacy"],
                    iso_time
                )
                bot_reply = f"📅 Scheduled for {parsed['publish_at']} — Video ID: {video_id}"

            elif parsed["action"] == "analytics":
                youtube_analytics, youtube = get_authenticated_service()
                channels_response = youtube.channels().list(part="snippet,statistics", mine=True).execute()
                stats = channels_response["items"][0]["statistics"]
                bot_reply = f"📊 Your channel has {stats['viewCount']} views, {stats['subscriberCount']} subscribers."
            else:
                # st.session_state.edited_video_path = handle_command(st.session_state.edited_video_path, user_input)
                # bot_reply = f"✅ performing action."
                # video_placeholder.video(st.session_state.edited_video_path)
                response = model.generate_content(user_input)
                bot_reply = response.text
        except Exception as e:
            response = model.generate_content(user_input)
            bot_reply = response.text

        st.session_state.chat_history.append(("bot", bot_reply))




        # if st.button("🧹 Clear Chat"):
        #     st.session_state.chat_history = []

    # for role, message in st.session_state.chat_history:
    #     if role == "user":
    #         align, bg = "right", "#e0f3ff"
    #     else:
    #         align, bg = "left", "#f2f2f2"
    #     st.markdown(f"""
    #         <div style="
    #             text-align: {align};
    #             background-color: {bg};
    #             padding: 8px;
    #             border-radius: 8px;
    #             margin: 5px 0;
    #         ">
    #             <b>{role.title()}:</b> {message}
    #         </div>
    #     """, unsafe_allow_html=True)

    pairs = []
    i = 0
    while i < len(st.session_state.chat_history):
        if i + 1 < len(st.session_state.chat_history):
            pairs.append([st.session_state.chat_history[i], st.session_state.chat_history[i + 1]])
            i += 2
        else:
            pairs.append([st.session_state.chat_history[i]])
            i += 1

    # Reverse the pairs to show the latest at the top
    for pair in reversed(pairs):
        for role, message in pair:
            align, bg = ("right", "#e0f3ff") if role == "user" else ("left", "#f2f2f2")
            st.markdown(f"""
                <div style="
                    text-align: {align};
                    background-color: {bg};
                    padding: 8px;
                    border-radius: 8px;
                    margin: 5px 0;
                ">
                    <b>{role.title()}:</b> {message}
                </div>
            """, unsafe_allow_html=True)
