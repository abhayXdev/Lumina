import os
import json
import requests
import asyncio
import edge_tts
import time
import socket
from flask import Flask, request, jsonify, send_from_directory, render_template, Response
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types
import yt_dlp

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='templates')
CORS(app)

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ESP32_IP = os.getenv("ESP32_IP", "192.168.1.100") 
STATIC_DIR = "static"
TTS_FILENAME = "reply.mp3"

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)
if GEMINI_API_KEY:
    print(f"--- Gemini Loaded (Key: {GEMINI_API_KEY[:8]}...) ---")

def get_ai_response(prompt, retries=3):
    """Attempt to get response using verified 2026 models."""
    models_to_try = [
        'gemini-3.1-flash-lite',
        'gemini-2.5-flash-lite',
        'gemini-2.5-flash'
    ]
    
    for attempt in range(retries):
        last_error = None
        for model_name in models_to_try:
            try:
                print(f"Attempting AI request with model: {model_name} (Attempt {attempt+1})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                return response.text
            except Exception as e:
                last_error = e
                err_str = str(e).upper()
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"Model {model_name} quota hit. Switching...")
                    continue
                if "404" in err_str:
                    print(f"Model {model_name} not found (404). Skipping...")
                    continue
                if "503" in err_str:
                    print(f"Model {model_name} busy (503).")
                    continue
                print(f"Model {model_name} failed: {e}")
                continue
        
        if attempt < retries - 1:
            wait_time = (attempt + 1) * 2
            print(f"All models busy or unavailable. Retrying in {wait_time}s...")
            time.sleep(wait_time)
        else:
            raise last_error

def verify_stream_url(url):
    """Check if the extracted URL is actually playable."""
    try:
        r = requests.get(url, stream=True, timeout=5)
        playable = r.status_code in [200, 206]
        r.close()
        return playable
    except:
        return False

def get_jiosaavn_music(query):
    """Search JioSaavn using stable 2026 mirrors."""
    mirrors = ["https://saavn.sumit.co", "https://jio-saavan-api.vercel.app", "https://jiosaavn-api-v3.vercel.app"]
    headers = {"User-Agent": "Mozilla/5.0"}
    for base in mirrors:
        try:
            url = f"{base}/api/search/songs?query={query}"
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("data", [])
                if isinstance(results, dict): results = results.get("results", [])
                if results:
                    song = results[0]
                    durls = song.get("downloadUrl") or song.get("download_url")
                    if durls:
                        link = durls[-1].get("link") if isinstance(durls[-1], dict) else durls[-1]
                        if link and verify_stream_url(link):
                            print(f"SUCCESS (JioSaavn): {song.get('name')}")
                            return link
        except: continue
    return None

def download_youtube_audio(query):
    """Download the song locally as an MP3 using the user's working yt-dlp config."""
    print(f"Downloading YouTube audio for: {query}")
    song_filename = "current_song"
    song_path = os.path.join(STATIC_DIR, song_filename)
    
    # Clean up old files
    for ext in ['mp3', 'm4a', 'webm', 'part']:
        filepath = os.path.join(STATIC_DIR, f"{song_filename}.{ext}")
        if os.path.exists(filepath):
            try: os.remove(filepath)
            except: pass

    # Exact options matching the user's successful command: yt-dlp -x --audio-format mp3
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128', # 128kbps is perfect for ESP32
        }],
        'outtmpl': os.path.join(STATIC_DIR, f'{song_filename}.%(ext)s'),
        'default_search': 'ytsearch1',
        'quiet': False, # Show download progress in terminal
        'nocheckcertificate': True,
        'ignoreerrors': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])
        
        # Check if the MP3 was created successfully
        mp3_file = f"{song_filename}.mp3"
        if os.path.exists(os.path.join(STATIC_DIR, mp3_file)):
            print(f"SUCCESS: Downloaded {mp3_file} locally.")
            return mp3_file
    except Exception as e:
        print(f"yt-dlp download failed: {e}")
        
    return None

@app.route('/stream')
def stream_audio():
    query = request.args.get('query')
    if not query: return "No query", 400
    
    print(f"Resolving stream for: {query}")
    # Failsafe Chain
    stream_url = get_jiosaavn_music(query)
    
    # If JioSaavn works, proxy it
    if stream_url:
        def generate():
            try:
                r = requests.get(stream_url, stream=True, timeout=15)
                for chunk in r.iter_content(chunk_size=4096):
                    yield chunk
            except Exception as e:
                print(f"Streaming error: {e}")
        return Response(generate(), mimetype='audio/aac')
    else:
        return "JioSaavn failed, fallback to download triggered", 404

async def generate_tts(text, output_path):
    try:
        communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"TTS Error: {e}")
        return False

def command_esp32(endpoint, params=None):
    try:
        esp_url = f"http://{ESP32_IP}/{endpoint}"
        print(f"Commanding ESP32: {esp_url} with {params}")
        requests.get(esp_url, params=params, timeout=10)
        return True
    except Exception as e:
        print(f"ESP32 Command Error: {e}")
        return False

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception: IP = '127.0.0.1'
    finally: s.close()
    return IP

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(STATIC_DIR, path)

@app.route('/stop', methods=['POST'])
def stop_music():
    command_esp32("stop")
    return jsonify({"status": "stopped"})

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get("msg")
    if not user_msg: return jsonify({"error": "No message"}), 400

    print(f"User: {user_msg}")

    try:
        prompt = f"""Act as Jarvis, a smart music assistant.
User says: "{user_msg}"

Response MUST be pure JSON format:
{{
    "reply": "your verbal response",
    "intent": "play" or "talk",
    "query": "song name if intent is play"
}}"""
        raw_text = get_ai_response(prompt)
        print(f"AI Response: {raw_text}")
        
        try:
            res_data = json.loads(raw_text.strip())
        except:
            if "{" in raw_text:
                res_data = json.loads(raw_text[raw_text.find("{"):raw_text.rfind("}")+1])
            else: raise ValueError("JSON parse error")

        reply_text = res_data.get("reply", "Ready.")
        intent = res_data.get("intent", "talk")
        query = res_data.get("query", "")

        # 1. Voice
        tts_path = os.path.join(STATIC_DIR, TTS_FILENAME)
        asyncio.run(generate_tts(reply_text, tts_path))
        
        # 2. Speak via SD
        local_ip = get_local_ip()
        tts_url = f"http://{local_ip}:5000/static/{TTS_FILENAME}"
        command_esp32("playTTS", {"url": tts_url})

        # 3. Play Music
        if intent == "play" and query:
            # First try the fast JioSaavn proxy
            jio_url = get_jiosaavn_music(query)
            if jio_url:
                proxy_url = f"http://{local_ip}:5000/stream?query={requests.utils.quote(query)}"
                time.sleep(6) 
                command_esp32("play", {"url": proxy_url})
            else:
                print("JioSaavn unavailable. Downloading via YouTube...")
                # If JioSaavn fails, fall back to downloading via YouTube (matching user's CLI test)
                # Since ESP32 is currently busy speaking the TTS intro (~3-6 seconds), 
                # we have the perfect window to download the MP3 in the background!
                song_filename = download_youtube_audio(query)
                if song_filename:
                    # Serve the locally downloaded MP3 file
                    local_song_url = f"http://{local_ip}:5000/static/{song_filename}"
                    # Add a tiny buffer if download was very fast
                    time.sleep(2) 
                    command_esp32("play", {"url": local_song_url})
                else:
                    reply_text += " (But I couldn't download that song.)"

        return jsonify({"reply": reply_text, "intent": intent, "query": query})

    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
