from flask import Flask, Response, request
import requests
import urllib.parse

app = Flask(__name__)

@app.route('/api/stream')
def stream_video():
    video_url = request.args.get('url')
    if not video_url:
        return "URL Eksik", 400

    parsed = urllib.parse.urlparse(video_url)
    domain = f"{parsed.scheme}://{parsed.netloc}/"
    
    # 1. TV'nin kimliğini gizleyip orijinal siteye bağlıyoruz
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": domain,
        "Origin": domain.rstrip('/'),
        # KRİTİK AYAR: Sitenin videoyu zipleyerek (gzip) göndermesini engeller, donmayı kökten çözer
        "Accept-Encoding": "identity", 
        "Connection": "keep-alive"
    }

    # 2. İLERİ/GERİ SARMA (SEEKING) BÖLÜMÜ
    # TV'den gelen "Şu saniyeye atla" (Range) komutunu alıp anime sitesine iletiyoruz
    range_header = request.headers.get('Range')
    if range_header:
        headers['Range'] = range_header

    try:
        # stream=True ile videoyu belleğe almadan, anlık su borusu gibi aktarıyoruz
        req = requests.get(video_url, headers=headers, stream=True, timeout=20)
        
        def generate():
            # 256KB'lık parçalar yüksek çözünürlükte (1080p/2160p) akıcılık için en ideal boyuttur
            for chunk in req.iter_content(chunk_size=256 * 1024):
                if chunk:
                    yield chunk

        # 3. TV'YE YANIT VERME VE BAŞLIKLARI KORUMA
        # status_code 206 dönmesi, TV'ye "İleri sarabilirsin, destekliyorum" demektir.
        resp = Response(generate(), status=req.status_code)
        
        # Orijinal sitedeki video uzunluğu ve parça izinlerini TV'ye kopyalıyoruz
        for key in ['Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges']:
            if key in req.headers:
                resp.headers[key] = req.headers[key]
                
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
        
    except Exception as e:
        return f"Sunucu Hatasi: {str(e)}", 500

if __name__ == '__main__':
    app.run()
