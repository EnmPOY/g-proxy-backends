from flask import Flask, Response, request
import requests
import urllib.parse

app = Flask(__name__)

@app.route('/api/stream')
def stream_video():
    video_url = request.args.get('url')
    if not video_url:
        return "URL parameter is missing", 400

    parsed = urllib.parse.urlparse(video_url)
    domain = f"{parsed.scheme}://{parsed.netloc}/"
    
    # We forcefully inject the headers server-side. The TV/VLC never has to worry about this.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": domain,
        "Origin": domain.rstrip('/'),
        "Accept-Encoding": "identity", # Crucial: prevents VLC buffering issues
        "Connection": "keep-alive"
    }

    # Pass the Range header from VLC/TV to the Anime server to allow fast-forwarding
    range_header = request.headers.get('Range')
    if range_header:
        headers['Range'] = range_header

    try:
        # Stream the video data chunk by chunk
        req = requests.get(video_url, headers=headers, stream=True, timeout=20)
        
        def generate():
            for chunk in req.iter_content(chunk_size=1024 * 512): # 512KB chunks for high speed
                if chunk:
                    yield chunk

        # Send the response back to VLC/TV
        resp = Response(generate(), status=req.status_code)
        
        # Mirror crucial headers so VLC knows the video length and format
        for key in ['Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges']:
            if key in req.headers:
                resp.headers[key] = req.headers[key]
                
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
        
    except Exception as e:
        return f"Proxy Error: {str(e)}", 500

if __name__ == '__main__':
    app.run()
