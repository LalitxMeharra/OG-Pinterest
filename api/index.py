import json
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.pinterest.com/"
}

def extract_pin_id(url):
    """Short URL expand karke numeric Pin ID nikalta hai."""
    session = requests.Session()
    try:
        res = session.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, allow_redirects=True, timeout=10)
        final_url = res.url
        match = re.search(r'/pin/(\d+)', final_url)
        if match:
            return match.group(1), final_url, res.text
    except Exception:
        pass
    # Agar direct ID input me hi ho
    match = re.search(r'/pin/(\d+)', url)
    return (match.group(1), url, "") if match else (None, url, "")

def extract_pinterest_media(pin_url):
    pin_id, final_url, html_backup = extract_pin_id(pin_url)
    
    if not pin_id:
        return {"status": "error", "message": "Invalid Pinterest Link. Could not find Pin ID."}

    # API Strategy 1: PinResource Direct Endpoint
    api_url = "https://www.pinterest.com/resource/PinResource/get/"
    params = {
        "data": json.dumps({
            "options": {
                "id": pin_id,
                "field_set_key": "detailed"
            },
            "context": {}
        })
    }

    try:
        res = requests.get(api_url, params=params, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            data = res.json()
            pin_data = data.get("resource_response", {}).get("data", {})
            
            title = pin_data.get("title") or pin_data.get("grid_title") or "Pinterest Media"
            
            # 1. Video Check
            videos = pin_data.get("videos", {})
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
                    thumb = pin_data.get("images", {}).get("orig", {}).get("url") or ""
                    return {
                        "status": "success",
                        "type": "video",
                        "title": title,
                        "download_url": best_video,
                        "thumbnail": thumb
                    }

            # 2. 4K Original Image Check
            images = pin_data.get("images", {})
            orig_img = images.get("orig", {}).get("url")
            if orig_img:
                return {
                    "status": "success",
                    "type": "image",
                    "title": title,
                    "download_url": orig_img,
                    "thumbnail": orig_img
                }
    except Exception:
        pass

    # API Strategy 2: Pidgets Public API Fallback
    try:
        pidget_url = f"https://api.pinterest.com/v3/pidgets/pins/info/?pin_ids={pin_id}"
        p_res = requests.get(pidget_url, headers=HEADERS, timeout=10).json()
        pins_dict = p_res.get("data", {})
        if pin_id in pins_dict:
            p_data = pins_dict[pin_id]
            images = p_data.get("images", {})
            for key in ["orig", "564x", "474x"]:
                if key in images and images[key].get("url"):
                    orig_url = re.sub(r"/\d+x/", "/originals/", images[key]["url"])
                    return {
                        "status": "success",
                        "type": "image",
                        "title": p_data.get("description") or "Pinterest 4K Image",
                        "download_url": orig_url,
                        "thumbnail": orig_url
                    }
    except Exception:
        pass

    # Strategy 3: Regex Raw HTML Fallback
    if html_backup:
        mp4_matches = re.findall(r'https://v\.pinimg\.com/videos/[^\s"\'<>\\]+\.mp4', html_backup)
        if mp4_matches:
            return {
                "status": "success",
                "type": "video",
                "title": "Pinterest Master Video",
                "download_url": max(mp4_matches, key=len),
                "thumbnail": ""
            }

        orig_img_matches = re.findall(r'https://i\.pinimg\.com/originals/[^\s"\'<>\\]+\.(?:jpg|png|webp)', html_backup)
        if orig_img_matches:
            return {
                "status": "success",
                "type": "image",
                "title": "Pinterest 4K Image",
                "download_url": orig_img_matches[0],
                "thumbnail": orig_img_matches[0]
            }

    return {"status": "error", "message": "Media extract nahi ho paya. Pin public hai ya check karo."}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # 1. Fetch Endpoint
        if path == "/api/fetch":
            pin_url = params.get("url", [""])[0].strip()
            if not pin_url:
                self._send_json({"status": "error", "message": "URL parameter missing"}, 400)
                return

            result = extract_pinterest_media(pin_url)
            if result.get("status") == "success":
                media_type = result["type"]
                ext = "mp4" if media_type == "video" else "jpg"
                clean_title = re.sub(r'[^\w\s-]', '', result["title"]).strip().replace(' ', '_') or "pin_media"

                result["proxy_stream"] = f"/api/stream?url={urllib.parse.quote(result['download_url'])}&type={media_type}"
                result["proxy_download"] = f"/api/download?url={urllib.parse.quote(result['download_url'])}&filename={urllib.parse.quote(clean_title)}.{ext}"

            self._send_json(result)
            return

        # 2. Proxy Stream (Bypass CORS for in-app preview)
        elif path == "/api/stream":
            target_url = params.get("url", [""])[0]
            media_type = params.get("type", ["image"])[0]
            if not target_url:
                self._send_json({"error": "No stream URL specified"}, 400)
                return

            try:
                r = requests.get(target_url, headers=HEADERS, stream=True, timeout=20)
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4" if media_type == "video" else "image/jpeg")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        self.wfile.write(chunk)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        # 3. Direct Download Proxy (Forces instant download)
        elif path == "/api/download":
            target_url = params.get("url", [""])[0]
            filename = params.get("filename", ["pin_media.mp4"])[0]
            if not target_url:
                self._send_json({"error": "No download URL specified"}, 400)
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
