import requests
import sys

def test_music_flow(song_query):
    print(f"--- STARTING DEBUG TEST FOR: {song_query} ---")
    
    # 1. Test YouTube Extraction directly
    print("\n[Step 1] Testing YouTube Proxy Endpoint...")
    # We simulate what the ESP32 would do
    url = f"http://127.0.0.1:5000/stream?query={song_query}"
    
    try:
        # We only read a small chunk to see if the stream starts
        print(f"Connecting to: {url}")
        response = requests.get(url, stream=True, timeout=20)
        
        if response.status_code == 200:
            print("SUCCESS: Stream endpoint is reachable!")
            print(f"Content-Type: {response.headers.get('Content-Type')}")
            
            # Read first 10KB to verify data flow
            chunk = next(response.iter_content(chunk_size=10240))
            if len(chunk) > 0:
                print(f"SUCCESS: Received {len(chunk)} bytes of audio data. The proxy is working!")
            else:
                print("FAILURE: Stream connected but returned no data.")
        else:
            print(f"FAILURE: Server returned status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"ERROR during connection: {e}")

    print("\n--- DEBUG TEST COMPLETE ---")

if __name__ == "__main__":
    query = "Arijit Singh hits"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    test_music_flow(query)
