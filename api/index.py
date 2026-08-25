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
        res = session.get(pin_url, allow_redirects=True, timeout=15)
        final_url = res.url
        html_text = res.text
    except Exception as e:
        return {"status": "error", "message": f"Connection Error: {str(e)}"}

    match = re.search(r'/pin/(\d+)', final_url)
    pin_id = match.group(1) if match else None

    soup = BeautifulSoup(html_text, "html.parser")
    pws_script = soup.find("script", {"id": "__PWS_INITIAL_PROPS__"}) or soup.find("script", {"id": "__PWS_DATA__"})
    
    og_image = soup.find("meta", property="og:image")
    fallback_thumb = og_image["content"] if og_image and og_image.get("content") else ""

    if pws_script and pws_script.string and pin_id:
        try:
            data = json.loads(pws_script.string)
            pins = data.get("initialReduxState", {}).get("pins", {})
            if not pins:
                pins = data.get("props", {}).get("initialReduxState", {}).get("pins", {})
            
            target_pin = pins.get(pin_id)
            if target_pin:
                title = target_pin.get("title") or target_pin.get("grid_title") or target_pin.get("description") or "Pinterest Media"
                
                images_dict = target_pin.get("images", {})
                best_img = fallback_thumb
                for key in ["originals", "orig", "1200x", "736x", "474x"]:
                    if key in images_dict and images_dict[key].get("url"):
                        best_img = images_dict[key]["url"]
                        break
                
                pin_str = json.dumps(target_pin)
                
                mp4_urls = re.findall(r'https://v[0-9a-zA-Z-]*\.pinimg\.com/videos/[^\s"\'<>\\]+\.mp4', pin_str)
                if not mp4_urls:
                    escaped_mp4s = re.findall(r'https:\\/\\/v[0-9a-zA-Z-]*\.pinimg\.com\\/videos\\/[^\s"\'<>\\]+\.mp4', pin_str)
                    mp4_urls = [u.replace('\\/', '/') for u in escaped_mp4s]
                
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
                    return {"status": "success", "type": "video", "title": title, "url": best_video, "thumbnail": best_img}

                if best_img:
                    return {"status": "success", "type": "image", "title": title, "url": best_img, "thumbnail": best_img}
        except Exception:
            pass

    raw_mp4s = re.findall(r'https://v[0-9a-zA-Z-]*\.pinimg\.com/videos/[^\s"\'<>\\]+\.mp4', html_text)
    if raw_mp4s:
        best_video = max(raw_mp4s, key=len)
        return {"status": "success", "type": "video", "title": "Pinterest Video", "url": best_video, "thumbnail": fallback_thumb}
        
    raw_m3u8s = re.findall(r'https://v[0-9a-zA-Z-]*\.pinimg\.com/videos/[^\s"\'<>\\]+\.m3u8', html_text)
    if raw_m3u8s:
        for m3u8 in raw_m3u8s:
            converted = convert_m3u8_to_mp4(m3u8)
            if converted:
                return {"status": "success", "type": "video", "title": "Pinterest Video", "url": converted, "thumbnail": fallback_thumb}

    if fallback_thumb:
        safe_high_res = fallback_thumb.replace("236x", "736x").replace("474x", "736x")
        return {"status": "success", "type": "image", "title": "Pinterest Image", "url": safe_high_res, "thumbnail": fallback_thumb}

    return {"status": "error", "message": "Failed to extract media. Check if pin is public."}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.lower()
        params = urllib.parse.parse_qs(parsed.query)

        if "download" in path or ("url" in params and params.get("filename")):
            target_url = params.get("url", [""])[0]
            filename = params.get("filename", ["media.mp4"])[0]
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

        elif "fetch" in path or "url" in params:
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

        else:
            self._send_json({"error": "Not Found"}, 404)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
