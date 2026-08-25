import json
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def convert_m3u8_to_mp4(m3u8_url):
    if "/hls/" in m3u8_url: return m3u8_url.replace("/hls/", "/720p/").replace(".m3u8", ".mp4")
    if "/iht/hls/" in m3u8_url: return m3u8_url.replace("/iht/hls/", "/mc/720p/").replace(".m3u8", ".mp4")
    if "/mc/hls/" in m3u8_url: return m3u8_url.replace("/mc/hls/", "/mc/720p/").replace(".m3u8", ".mp4")
    return None

def extract_pinterest_media(pin_url):
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        res = session.get(pin_url, allow_redirects=True, timeout=12)
        final_url = res.url
        html_text = res.text
    except Exception as e:
        return {"status": "error", "message": f"Connection Error: {str(e)}"}

    match = re.search(r'/pin/(\d+)', final_url)
    pin_id = match.group(1) if match else None

    soup = BeautifulSoup(html_text, "html.parser")
    pws_script = soup.find("script", {"id": "__PWS_INITIAL_PROPS__"}) or soup.find("script", {"id": "__PWS_DATA__"})
    
    # Global Thumbnail Fallback
    og_image = soup.find("meta", property="og:image")
    global_thumb = re.sub(r"/\d+x/", "/originals/", og_image["content"]) if og_image and og_image.get("content") else ""

    if pws_script and pws_script.string and pin_id:
        try:
            data = json.loads(pws_script.string)
            pins = data.get("initialReduxState", {}).get("pins", {})
            if not pins:
                pins = data.get("props", {}).get("initialReduxState", {}).get("pins", {})
            
            target_pin = pins.get(pin_id)
            if target_pin:
                title = target_pin.get("title") or target_pin.get("grid_title") or target_pin.get("description") or "Pinterest Media"
                pin_str = json.dumps(target_pin)
                
                # Custom Thumbnail extraction
                thumb_url = global_thumb
                img_urls = re.findall(r'https://i\.pinimg\.com/originals/[^\s"\'<>\\]+\.(?:jpg|png|webp)', pin_str)
                if not img_urls:
                    escaped_imgs = re.findall(r'https:\\/\\/i\.pinimg\.com\\/originals\\/[^\s"\'<>\\]+\.(?:jpg|png|webp)', pin_str)
                    img_urls = [u.replace('\\/', '/') for u in escaped_imgs]
                if img_urls:
                    thumb_url = img_urls[0]

                # 1. MP4 Search
                mp4_urls = re.findall(r'https://v[0-9a-zA-Z-]*\.pinimg\.com/videos/[^\s"\'<>\\]+\.mp4', pin_str)
                if not mp4_urls:
                    escaped_mp4s = re.findall(r'https:\\/\\/v[0-9a-zA-Z-]*\.pinimg\.com\\/videos\\/[^\s"\'<>\\]+\.mp4', pin_str)
                    mp4_urls = [u.replace('\\/', '/') for u in escaped_mp4s]
                
                # 2. HLS Search
                if not mp4_urls:
                    m3u8_urls = re.findall(r'https://v[0-9a-zA-Z-]*\.pinimg\.com/videos/[^\s"\'<>\\]+\.m3u8', pin_str)
                    if not m3u8_urls:
                        escaped_m3u8s = re.findall(r'https:\\/\\/v[0-9a-zA-Z-]*\.pinimg\.com\\/videos\\/[^\s"\'<>\\]+\.m3u8', pin_str)
                        m3u8_urls = [u.replace('\\/', '/') for u in escaped_m3u8s]
                    
                    for m3u8 in m3u8_urls:
                        converted = convert_m3u8_to_mp4(m3u8)
                        if converted:
                            mp4_urls.append(converted)

                if mp4_urls:
                    best_video = max(mp4_urls, key=len)
                    for url in mp4_urls:
                        if '1080p' in url or '720p' in url or 'expMp4' in url:
                            best_video = url
                            break
                    return {"status": "success", "type": "video", "title": title, "url": best_video, "thumbnail": thumb_url}

                if img_urls:
                    return {"status": "success", "type": "image", "title": title, "url": img_urls[0], "thumbnail": img_urls[0]}
        except Exception:
            pass

    # GLOBAL FALLBACKS
    raw_mp4s = re.findall(r'https://v[0-9a-zA-Z-]*\.pinimg\.com/videos/[^\s"\'<>\\]+\.mp4', html_text)
    if raw_mp4s:
        best_video = max(raw_mp4s, key=len)
        return {"status": "success", "type": "video", "title": "Pinterest Video", "url": best_video, "thumbnail": global_thumb}
        
    raw_m3u8s = re.findall(r'https://v[0-9a-zA-Z-]*\.pinimg\.com/videos/[^\s"\'<>\\]+\.m3u8', html_text)
    if raw_m3u8s:
        for m3u8 in raw_m3u8s:
            converted = convert_m3u8_to_mp4(m3u8)
            if converted:
                return {"status": "success", "type": "video", "title": "Pinterest Video", "url": converted, "thumbnail": global_thumb}

    if global_thumb:
        return {"status": "success", "type": "image", "title": "Pinterest Image", "url": global_thumb, "thumbnail": global_thumb}

    return {"status": "error", "message": "Failed to extract media. Check if pin is public."}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.lower()
        params = urllib.parse.parse_qs(parsed.query)

        # ... (Stream and Download Proxy Routes remain exact same) ...
        # Fetch Route Updates
        if "fetch" in path or "url" in params:
            pin_url = params.get("url", [""])[0].strip()
            if not pin_url:
                self._send_json({"status": "error", "message": "Missing URL"}, 400)
                return

            result = extract_pinterest_media(pin_url)
            if result.get("status") == "success":
                safe_url = urllib.parse.quote(result['url'], safe='')
                ext = "mp4" if result["type"] == "video" else "jpg"
                clean_title = re.sub(r'[^\w\s-]', '', result["title"]).strip().replace(' ', '_') or "pin_media"
                result["proxy_download"] = f"/api/download?url={safe_url}&filename={urllib.parse.quote(clean_title)}.{ext}"

            self._send_json(result)
            return

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
