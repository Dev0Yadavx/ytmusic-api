from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from ytmusicapi import YTMusic
import requests
import json
import time
import hashlib

app = Flask(__name__)
CORS(app)

# Default public guest instance
yt_guest = YTMusic(language="hi", location="IN")

def generate_sapisid_hash(sapisid, origin="https://music.youtube.com"):
    """YouTube authentication ke liye SAPISIDHASH signature calculate karta hai."""
    timestamp = str(int(time.time()))
    sha1 = hashlib.sha1(f"{timestamp} {sapisid} {origin}".encode('utf-8')).hexdigest()
    return f"SAPISIDHASH {timestamp}_{sha1}"

def get_yt_client():
    raw_cookie = request.headers.get("X-User-Cookie", "").strip()

    if raw_cookie:
        try:
            # 1. Cookie string se individual cookies parse karna
            cookie_dict = {}
            for item in raw_cookie.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookie_dict[k.strip()] = v.strip()

            # 2. SAPISID ya __Secure-3PAPISID find karna
            sapisid = cookie_dict.get("SAPISID") or cookie_dict.get("__Secure-3PAPISID") or cookie_dict.get("__Secure-1PAPISID")

            headers_dict = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "hi,en-IN;q=0.9,en;q=0.8",
                "Content-Type": "application/json",
                "X-Origin": "https://music.youtube.com",
                "Origin": "https://music.youtube.com",
                "Cookie": raw_cookie
            }

            if sapisid:
                headers_dict["Authorization"] = generate_sapisid_hash(sapisid)

            return YTMusic(auth=json.dumps(headers_dict), language="hi", location="IN")
        except Exception as e:
            print("Auth Initialization Error:", e)

    return yt_guest

def parse_item(item):
    if not isinstance(item, dict):
        return None
    thumbs = item.get("thumbnails", [])
    thumb = thumbs[-1]["url"] if thumbs else ""
    artists = item.get("artists", [])
    if isinstance(artists, list) and len(artists) > 0:
        artist_name = ", ".join([a.get("name", "") for a in artists if isinstance(a, dict)])
    elif "author" in item:
        artist_name = item.get("author", "")
    elif "subtitle" in item:
        artist_name = item.get("subtitle", "")
    else:
        artist_name = "Various Artists"

    vid = item.get("videoId")
    pid = item.get("playlistId")
    bid = item.get("browseId")

    if vid:
        return {"id": vid, "title": item.get("title", ""), "subtitle": artist_name, "thumbnail": thumb, "type": "song"}
    elif pid:
        return {"id": pid, "title": item.get("title", ""), "subtitle": artist_name, "thumbnail": thumb, "type": "playlist"}
    elif bid:
        itype = "album" if "MPRE" in bid or "album" in str(item.get("title", "")).lower() else "artist"
        return {"id": bid, "title": item.get("title", ""), "subtitle": artist_name, "thumbnail": thumb, "type": itype}
    return None

# Root / Docs UI
@app.route("/")
@app.route("/index")
def index():
    return jsonify({
        "status": "online",
        "message": "YT Music Suite API with SAPISIDHASH Auto-Signer",
        "endpoints": {
            "public": ["/api/home/full", "/api/charts", "/api/regional", "/api/album", "/api/artist", "/api/playlist", "/api/search", "/api/suggestions", "/api/song", "/api/watch", "/api/lyrics"],
            "auth": ["/api/user/liked", "/api/user/playlists", "/api/user/artists", "/api/user/history"]
        }
    })

# ==========================================
# PUBLIC ENDPOINTS
# ==========================================

@app.route("/api/home/full")
def full_home_screen():
    country = request.args.get("country", "IN")
    yt = get_yt_client()
    res = {"status": "success", "sections": []}
    try:
        raw_home = yt.get_home(limit=5)
        for idx, sec in enumerate(raw_home):
            items = [parse_item(i) for i in sec.get("contents", []) if parse_item(i)]
            if items:
                res["sections"].append({
                    "section_id": f"carousel_{idx+1}",
                    "title": sec.get("title", "Recommended"),
                    "layout": "horizontal_carousel",
                    "items": items
                })
    except Exception:
        pass
    return jsonify(res)

@app.route("/api/charts")
def get_charts():
    country = request.args.get("country", "IN")
    try:
        yt = get_yt_client()
        return jsonify(yt.get_charts(country=country))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/regional")
def get_regional():
    lang = request.args.get("lang", "bhojpuri").lower().strip()
    q = f"Top {lang} songs 2026"
    try:
        yt = get_yt_client()
        results = yt.search(q, filter="songs", limit=25)
        return jsonify([parse_item(r) for r in results if parse_item(r)])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/album")
def get_album():
    aid = request.args.get("id")
    if not aid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        data = yt.get_album(aid)
        return jsonify({
            "title": data.get("title", ""),
            "year": data.get("year", ""),
            "thumbnail": data.get("thumbnails", [{}])[-1].get("url", ""),
            "tracks": [parse_item(t) for t in data.get("tracks", []) if parse_item(t)]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/artist")
def get_artist():
    aid = request.args.get("id")
    if not aid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        data = yt.get_artist(aid)
        return jsonify({
            "name": data.get("name", ""),
            "subscribers": data.get("subscribers", ""),
            "thumbnail": data.get("thumbnails", [{}])[-1].get("url", ""),
            "top_songs": [parse_item(s) for s in data.get("songs", {}).get("results", []) if parse_item(s)]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/playlist")
def get_playlist():
    pid = request.args.get("id")
    if not pid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        data = yt.get_playlist(pid, limit=100)
        return jsonify({
            "title": data.get("title", ""),
            "author": data.get("author", {}).get("name", ""),
            "tracks": [parse_item(t) for t in data.get("tracks", []) if parse_item(t)]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()
    f = request.args.get("filter", "songs")
    if not q: return jsonify([])
    try:
        yt = get_yt_client()
        results = yt.search(q, filter=f, limit=25, ignore_spelling=True)
        return jsonify([parse_item(r) for r in results if parse_item(r)])
    except Exception:
        return jsonify([])

@app.route("/api/suggestions")
def suggestions():
    q = request.args.get("q", "").strip()
    if not q: return jsonify([])
    try:
        url = f"https://suggestqueries.google.com/complete/search?client=youtube&ds=yt&hl=hi&gl=in&q={q}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        text = resp.text
        start, end = text.find("(") + 1, text.rfind(")")
        return jsonify([item[0] for item in json.loads(text[start:end])[1]])
    except Exception:
        return jsonify([q])

@app.route("/api/song")
def song_info():
    vid = request.args.get("id")
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        return jsonify(yt.get_song(vid))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watch")
def watch_queue():
    vid = request.args.get("id")
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        return jsonify(yt.get_watch_playlist(videoId=vid, limit=25))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/lyrics")
def get_lyrics():
    vid = request.args.get("id")
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        watch = yt.get_watch_playlist(videoId=vid, limit=3)
        lid = watch.get("lyrics")
        if lid:
            data = yt.get_lyrics(lid)
            return jsonify({"status": "success", "lyrics": data.get("lyrics", "")})
    except Exception:
        pass
    return jsonify({"status": "not_found", "message": "Lyrics not available"})

# ==========================================
# AUTHENTICATED USER ENDPOINTS
# ==========================================

@app.route("/api/user/liked")
def user_liked_songs():
    yt = get_yt_client()
    try:
        data = yt.get_liked_songs(limit=50)
        tracks = [parse_item(t) for t in data.get("tracks", []) if parse_item(t)]
        return jsonify({"title": "Aapke Liked Gane", "count": len(tracks), "tracks": tracks})
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

@app.route("/api/user/playlists")
def user_library_playlists():
    yt = get_yt_client()
    try:
        playlists = yt.get_library_playlists(limit=50)
        return jsonify([parse_item(p) for p in playlists if parse_item(p)])
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

@app.route("/api/user/artists")
def user_library_artists():
    yt = get_yt_client()
    try:
        artists = yt.get_library_subscriptions(limit=50)
        return jsonify([parse_item(a) for a in artists if parse_item(a)])
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

@app.route("/api/user/history")
def user_history():
    yt = get_yt_client()
    try:
        history = yt.get_history()
        return jsonify([parse_item(h) for h in history if parse_item(h)])
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
