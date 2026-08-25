import json
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def extract_pinterest_media(pin_url):
    session = requests.Session()
    try:
        res = session.get(pin_url, headers=HEADERS, allow_redirects=True, timeout=12)
        res.raise_for_status()
    except Exception as e:
        return {"status": "error", "message": f"URL resolve failed: {str(e)}"}

    soup = BeautifulSoup(res.text, "html.parser")
    pws_script = soup.find("script", {"id": "__PWS_DATA__"})
    
    if pws_script and pws_script.string:
        try:
            data = json.loads(pws_script.string)
            pins = data.get("props", {}).get("initialReduxState", {}).get("pins", {})
            for _, pin in pins.items():
                title = pin.get("title") or pin.get("grid_title") or "Pinterest Media"
                
                # Check for Best Video Stream
                videos = pin.get("videos", {})
                if videos and "video_list" in videos:
                    v_list = videos["video_list"]
                    best_url = None
                    max_w = 0
                    for _, val in v_list.items():
                        url = val.get("url", "")
                        width = val.get("width", 0)
                        if url.endswith(".mp4") and width >= max_w:
                            max_w = width
                            best_url = url
                    
                    if best_url:
                        thumb = pin.get("images", {}).get("orig", {}).get("url") or ""
                        return {
                            "status": "success",
                            "type": "video",
                            "title": title,
                            "download_url": best_url,
                            "thumbnail": thumb
                        }
                
                # Check for 4K / Original Image
                images = pin.get("images", {})
                orig_url = images.get("orig", {}).get("url")
                if orig_url:
                    return {
                        "status": "success",
                        "type": "image",
                        "title": title,
                        "download_url": orig_url,
                        "thumbnail": orig_url
                    }
        except Exception:
            pass

    # Method 2: OpenGraph & Tag Fallback
    og_video = soup.find("meta", property="og:video") or soup.find("meta", property="og:video:secure_url")
    og_image = soup.find("meta", property="og:image")
    og_title = soup.find("meta", property="og:title")
    title = og_title["content"] if og_title and og_title.get("content") else "Pinterest Media"

    if og_video and og_video.get("content"):
        return {
            "status": "success",
            "type": "video",
            "title": title,
            "download_url": og_video["content"],
            "thumbnail": og_image["content"] if og_image else ""
        }

    if og_image and og_image.get("content"):
        # Upgrade resolution to /originals/
        high_res = re.sub(r"/\d+x/", "/originals/", og_image["content"])
        return {
            "status": "success",
            "type": "image",
            "title": title,
            "download_url": high_res,
            "thumbnail": high_res
        }

    return {"status": "error", "message": "Failed to parse media. Ensure the Pin is public."}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # 1. API Fetch Info
        if path == "/api/fetch":
            pin_url = params.get("url", [""])[0].strip()
            if not pin_url:
                self._send_json({"status": "error", "message": "Missing URL parameter"}, 400)
                return

            result = extract_pinterest_media(pin_url)
            if result.get("status") == "success":
                # Create our own proxy routes
                media_type = result["type"]
                clean_title = re.sub(r'[^\w\s-]', '', result["title"]).strip().replace(' ', '_') or "media"
                ext = "mp4" if media_type == "video" else "jpg"
                
                proxy_stream = f"/api/stream?url={urllib.parse.quote(result['download_url'])}&type={media_type}"
                proxy_dl = f"/api/download?url={urllib.parse.quote(result['download_url'])}&filename={urllib.parse.quote(clean_title)}.{ext}"
                
                result["proxy_stream"] = proxy_stream
                result["proxy_download"] = proxy_dl

            self._send_json(result)
            return

        # 2. Proxy Stream (Bypasses CORS for direct preview)
        elif path == "/api/stream":
            target_url = params.get("url", [""])[0]
            media_type = params.get("type", ["image"])[0]
            if not target_url:
                self._send_json({"error": "No stream target"}, 400)
                return

            try:
                r = requests.get(target_url, headers=HEADERS, stream=True, timeout=20)
                self.send_response(200)
                content_type = "video/mp4" if media_type == "video" else "image/jpeg"
                self.send_header("Content-Type", content_type)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        self.wfile.write(chunk)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        # 3. Direct Download Proxy (Forces browser download with custom filename)
        elif path == "/api/download":
            target_url = params.get("url", [""])[0]
            filename = params.get("filename", ["pinterest_media.mp4"])[0]
            if not target_url:
                self._send_json({"error": "No download target"}, 400)
                return

            try:
                r = requests.get(target_url, headers=HEADERS, stream=True, timeout=20)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Access-Control-Allow-Origin", "*")
                if "content-length" in r.headers:
                    self.send_header("Content-Length", r.headers["content-length"])
                self.end_headers()
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        self.wfile.write(chunk)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        else:
            self._send_json({"error": "Not Found"}, 404)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
