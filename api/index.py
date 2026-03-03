from flask import Flask, Response, request
import requests
import urllib.parse

app = Flask(__name__)

def get_dynamic_headers(video_url):
    parsed = urllib.parse.urlparse(video_url)
    domain = f"{parsed.scheme}://{parsed.netloc}/"
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": domain,
        "Origin": domain.rstrip('/'),
        "Accept": "*/*",
        "Connection": "keep-alive"
    }

@app.route('/api/stream')
def stream_video():
    video_url = request.args.get('url')
    if not video_url:
        return "URL parametresi eksik", 400

    headers = get_dynamic_headers(video_url)
    
    # TV'den (SSIPTV) gelen ileri/geri sarma veya parçalı indirme (Range) isteklerini yakala
    range_header = request.headers.get('Range', None)
    if range_header:
        headers['Range'] = range_header

    try:
        # Asıl sunucuya istek atıyoruz
        req = requests.get(video_url, headers=headers, stream=True, timeout=15)
        
        def generate():
            # Yüksek hız için 1 MB paketler
            for chunk in req.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    yield chunk

        # Yanıtı TV'ye iletirken HTTP durum kodunu (200 veya 206) koruyoruz
        resp = Response(generate(), status=req.status_code)
        
        # Orijinal sunucudan gelen video başlıklarını (Content-Type vb.) TV'ye aktarıyoruz
        resp.headers['Content-Type'] = req.headers.get('Content-Type', 'video/mp4')
        resp.headers['Access-Control-Allow-Origin'] = '*'
        
        # Parçalı akış (Range) için zorunlu başlıklar
        if 'Content-Range' in req.headers:
            resp.headers['Content-Range'] = req.headers['Content-Range']
        if 'Accept-Ranges' in req.headers:
            resp.headers['Accept-Ranges'] = req.headers['Accept-Ranges']
        if 'Content-Length' in req.headers:
            resp.headers['Content-Length'] = req.headers['Content-Length']
            
        return resp
        
    except Exception as e:
        return f"Sunucu Hatasi: {str(e)}", 500

# Vercel için uygulamanın dışa aktarılması
if __name__ == '__main__':
    app.run()
