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
        res = session.get(pin_url, allow_redirects=True, timeout=12)
        html_text = res.text
    except Exception as e:
        return {"status": "error", "message": f"URL Connection Failed: {str(e)}"}

    # 1. Primary Strategy: __PWS_DATA__ Embedded JSON
    soup = BeautifulSoup(html_text, "html.parser")
    pws_script = soup.find("script", {"id": "__PWS_DATA__"})
    
    if pws_script and pws_script.string:
        try:
            data = json.loads(pws_script.string)
            pins = data.get("props", {}).get("initialReduxState", {}).get("pins", {})
            for _, pin in pins.items():
                title = pin.get("title") or pin.get("grid_title") or "Pinterest Media"
                
                # Videos (MP4)
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
                            "download_url": best_video,
                            "thumbnail": thumb
                        }

                # 4K / Original Raw Images
                images = pin.get("images", {})
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

    # 2. Regex Fallback for Videos
    mp4_matches = re.findall(r'https://v\.pinimg\.com/videos/[^\s"\'<>\\]+\.mp4', html_text)
    if mp4_matches:
        return {
            "status": "success",
            "type": "video",
            "title": "Pinterest Master Video",
            "download_url": max(mp4_matches, key=len),
            "thumbnail": ""
        }

    # 3. Regex Fallback for 4K Images
    orig_img_matches = re.findall(r'https://i\.pinimg\.com/originals/[^\s"\'<>\\]+\.(?:jpg|png|webp)', html_text)
    if orig_img_matches:
        return {
            "status": "success",
            "type": "image",
            "title": "Pinterest 4K Image",
            "download_url": orig_img_matches[0],
            "thumbnail": orig_img_matches[0]
        }

    # 4. OpenGraph Fallback
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
        high_res = re.sub(r"/\d+x/", "/originals/", og_image["content"])
        return {
            "status": "success",
            "type": "image",
            "title": title,
            "download_url": high_res,
            "thumbnail": high_res
        }

    return {"status": "error", "message": "Media extract nahi ho paya. Pin public hai ya check karo."}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.lower()
        params = urllib.parse.parse_qs(parsed.query)

        # 1. STREAM PROXY ROUTE
        if "stream" in path or ("url" in params and params.get("type")):
            target_url = params.get("url", [""])[0]
            media_type = params.get("type", ["image"])[0]
            if not target_url:
                self._send_json({"error": "No target URL"}, 400)
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

        # 2. DOWNLOAD PROXY ROUTE
        elif "download" in path or ("url" in params and params.get("filename")):
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

        # 3. FETCH / MAIN ENDPOINT (Catches /api/fetch, /api/index.py, or any request with ?url=)
        elif "fetch" in path or "url" in params:
            pin_url = params.get("url", [""])[0].strip()
            if not pin_url:
                self._send_json({"status": "error", "message": "Missing URL parameter"}, 400)
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

        else:
            self._send_json({"error": "Endpoint not recognized", "received_path": self.path}, 404)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
