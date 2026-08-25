import json
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.pinterest.com/"
}

def extract_pinterest_media(pin_url):
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        # Redirect follow karke actual pin page fetch karna
        res = session.get(pin_url, allow_redirects=True, timeout=12)
        html_text = res.text
    except Exception as e:
        return {"status": "error", "message": f"Connection Error: {str(e)}"}

    soup = BeautifulSoup(html_text, "html.parser")

    # 1. PRIORITY 1: Video Parsing from __PWS_DATA__ JSON
    pws_script = soup.find("script", {"id": "__PWS_DATA__"})
    if pws_script and pws_script.string:
        try:
            data = json.loads(pws_script.string)
            pins = data.get("props", {}).get("initialReduxState", {}).get("pins", {})
            for _, pin in pins.items():
                title = pin.get("title") or pin.get("grid_title") or "Pinterest Media"
                
                # Check Standard Video Pin
                videos = pin.get("videos", {})
                if videos and "video_list" in videos:
                    v_list = videos["video_list"]
                    best_video = None
                    max_w = 0
                    for _, val in v_list.items():
                        url = val.get("url", "")
                        width = val.get("width", 0)
                        if url.endswith(".mp4") and width >= max_w:
                            max_w = width
                            best_video = url
                    
                    if best_video:
                        thumb = pin.get("images", {}).get("orig", {}).get("url") or ""
                        return {
                            "status": "success",
                            "type": "video",
                            "title": title,
                            "url": best_video,
                            "thumbnail": thumb
                        }

                # Check Story / Idea Pin Video
                story_data = pin.get("story_pin_data", {})
                pages = story_data.get("pages", []) if story_data else []
                for page in pages:
                    blocks = page.get("blocks", [])
                    for block in blocks:
                        if block.get("video"):
                            v_list = block.get("video", {}).get("video_list", {})
                            for _, val in v_list.items():
                                if val.get("url", "").endswith(".mp4"):
                                    return {
                                        "status": "success",
                                        "type": "video",
                                        "title": title,
                                        "url": val.get("url"),
                                        "thumbnail": ""
                                    }

                # High-Res 4K Image Pin
                images = pin.get("images", {})
                orig_img = images.get("orig", {}).get("url")
                if orig_img:
                    return {
                        "status": "success",
                        "type": "image",
                        "title": title,
                        "url": orig_img,
                        "thumbnail": orig_img
                    }
        except Exception:
            pass

    # 2. PRIORITY 2: Direct Video Tag & Regex Fallbacks
    mp4_urls = re.findall(r'https://v\.pinimg\.com/videos/[^\s"\'<>\\]+\.mp4', html_text)
    if mp4_urls:
        best_mp4 = max(mp4_urls, key=len)
        return {
            "status": "success",
            "type": "video",
            "title": "Pinterest Master Video",
            "url": best_mp4,
            "thumbnail": ""
        }

    # Video Meta Tag Fallback
    og_video = soup.find("meta", property="og:video") or soup.find("meta", property="og:video:secure_url")
    if og_video and og_video.get("content"):
        return {
            "status": "success",
            "type": "video",
            "title": "Pinterest Master Video",
            "url": og_video["content"],
            "thumbnail": ""
        }

    # 3. PRIORITY 3: Original 4K Image Fallback
    orig_img_matches = re.findall(r'https://i\.pinimg\.com/originals/[^\s"\'<>\\]+\.(?:jpg|png|webp)', html_text)
    if orig_img_matches:
        return {
            "status": "success",
            "type": "image",
            "title": "Pinterest 4K Image",
            "url": orig_img_matches[0],
            "thumbnail": orig_img_matches[0]
        }

    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        high_res = re.sub(r"/\d+x/", "/originals/", og_image["content"])
        return {
            "status": "success",
            "type": "image",
            "title": "Pinterest Image",
            "url": high_res,
            "thumbnail": high_res
        }

    return {"status": "error", "message": "Media extract nahi ho paya. Pin public hai ya check karo."}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        pin_url = params.get("url", [""])[0].strip()
        if not pin_url:
            self._send_json({"status": "error", "message": "Missing URL parameter"}, 400)
            return

        result = extract_pinterest_media(pin_url)
        self._send_json(result)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
