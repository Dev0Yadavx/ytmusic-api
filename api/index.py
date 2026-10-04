from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from ytmusicapi import YTMusic
import requests
import json
import os
import yt_dlp

app = Flask(__name__)
CORS(app)
yt = YTMusic()

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

# Serve Liquid Glass Docs UI
@app.route("/")
def index():
    docs_path = os.path.join(os.path.dirname(__file__), "ytmusic_docs.html")
    if os.path.exists(docs_path):
        return send_file(docs_path)
    return jsonify({"status": "online", "message": "YT Music API is Running"})

# 1. Full Home Screen Engine
@app.route("/api/home/full")
def full_home_screen():
    country = request.args.get("country", "IN")
    home_response = {
        "status": "success",
        "header_chips": [
            {"label": "Energize", "params": "ggMPOg1uX1B2MVFqSkVzU1E%3D"},
            {"label": "Relax", "params": "ggMPOg1uX3ZfM1d1ek9CSlE%3D"},
            {"label": "Workout", "params": "ggMPOg1uX254UllOdlJGUUE%3D"},
            {"label": "Commute", "params": "ggMPOg1uX0d4aXhzTWFUWUE%3D"},
            {"label": "Focus", "params": "ggMPOg1uX01ZUWJ4Z3c4M1E%3D"}
        ],
        "sections": []
    }

    try:
        charts = yt.get_charts(country=country)
        songs = charts.get("songs", {}).get("items", [])
        if songs:
            cleaned_picks = [parse_item(s) for s in songs[:20] if parse_item(s)]
            home_response["sections"].append({
                "section_id": "quick_picks",
                "title": "Quick Picks",
                "layout": "grid_compact",
                "items": cleaned_picks
            })
    except Exception:
        pass

    try:
        raw_home = yt.get_home(limit=8)
        for idx, sec in enumerate(raw_home):
            contents = sec.get("contents", [])
            cleaned_contents = [parse_item(i) for i in contents if parse_item(i)]
            if cleaned_contents:
                home_response["sections"].append({
                    "section_id": f"carousel_{idx+1}",
                    "title": sec.get("title", "Recommended"),
                    "layout": "horizontal_carousel",
                    "items": cleaned_contents
                })
    except Exception:
        pass

    try:
        if 'charts' in locals() and charts.get("videos", {}).get("items"):
            vids = charts["videos"]["items"]
            cleaned_vids = [parse_item(v) for v in vids[:15] if parse_item(v)]
            if cleaned_vids:
                home_response["sections"].append({
                    "section_id": "trending_videos",
                    "title": "Trending Music Videos",
                    "layout": "horizontal_carousel_video",
                    "items": cleaned_vids
                })
    except Exception:
        pass

    try:
        if 'charts' in locals() and charts.get("artists", {}).get("items"):
            arts = charts["artists"]["items"]
            cleaned_arts = []
            for a in arts[:12]:
                thumbs = a.get("thumbnails", [])
                cleaned_arts.append({
                    "id": a.get("browseId", ""),
                    "title": a.get("title", ""),
                    "subtitle": a.get("subscribers", "Artist"),
                    "thumbnail": thumbs[-1]["url"] if thumbs else "",
                    "type": "artist"
                })
            if cleaned_arts:
                home_response["sections"].append({
                    "section_id": "top_artists",
                    "title": "Popular Artists",
                    "layout": "circular_carousel",
                    "items": cleaned_arts
                })
    except Exception:
        pass

    return jsonify(home_response)

# 2. Charts
@app.route("/api/charts")
def get_charts():
    country = request.args.get("country", "IN")
    try:
        return jsonify(yt.get_charts(country=country))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. Search
@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()
    f = request.args.get("filter", "songs")
    if not q: return jsonify([])
    try:
        results = yt.search(q, filter=f, limit=25, ignore_spelling=True)
        return jsonify([parse_item(r) for r in results if parse_item(r)])
    except Exception:
        try:
            return jsonify(yt.search(q, limit=20))
        except Exception:
            return jsonify([])

# 4. Instant Autocomplete
@app.route("/api/suggestions")
def suggestions():
    q = request.args.get("q", "").strip()
    if not q: return jsonify([])
    try:
        url = f"https://suggestqueries.google.com/complete/search?client=youtube&ds=yt&q={q}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        text = resp.text
        start, end = text.find("(") + 1, text.rfind(")")
        return jsonify([item[0] for item in json.loads(text[start:end])[1]])
    except Exception:
        return jsonify([q])

# 5. Moods & Genres
@app.route("/api/moods")
def moods():
    try:
        return jsonify(yt.get_mood_categories())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 6. Song Metadata
@app.route("/api/song")
def song_info():
    vid = request.args.get("id")
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        return jsonify(yt.get_song(vid))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 7. Radio Queue
@app.route("/api/watch")
def watch_queue():
    vid = request.args.get("id")
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        return jsonify(yt.get_watch_playlist(videoId=vid, limit=50))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 8. Lyrics Summary
@app.route("/api/lyrics")
def get_lyrics():
    vid = request.args.get("id")
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        watch = yt.get_watch_playlist(videoId=vid, limit=5)
        lid = watch.get("lyrics")
        if lid:
            data = yt.get_lyrics(lid)
            return jsonify({"status": "success", "lyrics": data.get("lyrics", "")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"status": "not_found", "message": "Lyrics not available"})

# 9. Serverless-Safe Audio Stream Resolver (Direct yt_dlp module)
@app.route("/api/stream")
def get_stream():
    vid = request.args.get("id")
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            stream_url = info.get('url')
            return jsonify({"videoId": vid, "stream_url": stream_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 10. Refresh
@app.route("/api/refresh", methods=["POST", "GET"])
def refresh_session():
    global yt
    yt = YTMusic()
    return jsonify({"status": "success", "message": "Guest session refreshed"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
