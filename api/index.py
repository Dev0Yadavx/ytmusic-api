from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from ytmusicapi import YTMusic
import requests
import json

app = Flask(__name__)
CORS(app)

yt_guest = YTMusic()

# Raw Browser Cookie String ko ytmusicapi compatible headers me convert karta hai
def get_yt_client():
    raw_cookie = request.headers.get("X-User-Cookie")
    auth_header = request.headers.get("Authorization")

    if raw_cookie:
        try:
            # Agar direct raw cookie string aayi hai browser webview se
            headers_dict = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Content-Type": "application/json",
                "X-Origin": "https://music.youtube.com",
                "Cookie": raw_cookie
            }
            return YTMusic(auth=json.dumps(headers_dict))
        except Exception as e:
            print("Cookie init error:", e)

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        try:
            return YTMusic(auth=token)
        except Exception:
            pass

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

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>YT Music Suite - Web Login & Data</title>
    <style>
        :root {
            --pink: #ff2a85;
            --yellow: #ffe600;
            --glass: rgba(255, 255, 255, 0.08);
            --border: rgba(255, 255, 255, 0.2);
            --bg: #0a040c;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, sans-serif; }
        body { background: var(--bg); color: #fff; padding: 14px; min-height: 100vh; }
        .glass-panel { background: var(--glass); backdrop-filter: blur(20px); border: 1px solid var(--border); border-radius: 16px; padding: 16px; margin-bottom: 12px; }
        .btn { background: linear-gradient(135deg, var(--pink), #ff6097); border: none; color: #fff; padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; cursor: pointer; }
        .btn.outline { background: transparent; border: 1px solid var(--border); }
        .song-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
        .song-item img { width: 44px; height: 44px; border-radius: 8px; object-fit: cover; }
        .song-info h4 { font-size: 13px; margin-bottom: 2px; }
        .song-info p { font-size: 11px; color: rgba(255,255,255,0.6); }
    </style>
</head>
<body>
    <div class="glass-panel" style="display:flex; justify-content:space-between; align-items:center;">
        <h2 style="font-size:16px;"><span style="color:var(--pink);">YT</span> Music Session</h2>
        <button class="btn" id="loginBtn" onclick="openLoginWindow()">Login with Google</button>
    </div>

    <!-- Login Instructions Modal/Card -->
    <div class="glass-panel" id="sessionBox" style="display:none;">
        <h3 style="font-size:14px; color:var(--yellow); margin-bottom:8px;">Active Session Detected</h3>
        <div style="display:flex; gap:8px;">
            <button class="btn outline" onclick="loadUserLiked()">Fetch Liked Songs</button>
            <button class="btn outline" onclick="loadUserPlaylists()">Fetch My Playlists</button>
            <button class="btn outline" onclick="loadUserHistory()">Fetch History</button>
            <button class="btn" style="background:#ff4e45;" onclick="logout()">Logout</button>
        </div>
    </div>

    <div class="glass-panel">
        <h3 id="sectionTitle" style="font-size:14px; margin-bottom:12px;">Public Trending</h3>
        <div id="songsList">Loading trending...</div>
    </div>

    <script>
        const BASE = window.location.origin;
        let userCookie = localStorage.getItem("yt_cookie") || "";

        function checkSession() {
            if (userCookie) {
                document.getElementById("sessionBox").style.display = "block";
                document.getElementById("loginBtn").innerText = "Account Connected";
                document.getElementById("loginBtn").style.background = "#4ade80";
                loadUserLiked();
            } else {
                document.getElementById("sessionBox").style.display = "none";
                document.getElementById("loginBtn").innerText = "Login with Google";
                loadPublicHome();
            }
        }

        // Web Browser / Desktop Login helper (Popup)
        function openLoginWindow() {
            const cookieStr = prompt("Android App me WebView automatic login karega. Web par test karne ke liye YouTube Music se Cookie paste karein:");
            if (cookieStr && cookieStr.trim().length > 10) {
                localStorage.setItem("yt_cookie", cookieStr.trim());
                userCookie = cookieStr.trim();
                checkSession();
            }
        }

        function logout() {
            localStorage.removeItem("yt_cookie");
            userCookie = "";
            checkSession();
        }

        async function loadPublicHome() {
            document.getElementById("sectionTitle").innerText = "Trending Songs (Public)";
            const res = await fetch(BASE + "/api/home/full?country=IN");
            const data = await res.json();
            const items = data.sections[0]?.items || [];
            renderItems(items);
        }

        async function loadUserLiked() {
            document.getElementById("sectionTitle").innerText = "Your Liked Songs";
            document.getElementById("songsList").innerText = "Fetching your private library...";
            try {
                const res = await fetch(BASE + "/api/user/liked", {
                    headers: { "X-User-Cookie": userCookie }
                });
                const data = await res.json();
                renderItems(data.tracks || []);
            } catch(e) {
                document.getElementById("songsList").innerText = "Failed: " + e.message;
            }
        }

        async function loadUserPlaylists() {
            document.getElementById("sectionTitle").innerText = "Your Playlists";
            document.getElementById("songsList").innerText = "Fetching...";
            try {
                const res = await fetch(BASE + "/api/user/playlists", {
                    headers: { "X-User-Cookie": userCookie }
                });
                const data = await res.json();
                renderItems(data);
            } catch(e) {
                document.getElementById("songsList").innerText = "Failed: " + e.message;
            }
        }

        async function loadUserHistory() {
            document.getElementById("sectionTitle").innerText = "Recently Played History";
            document.getElementById("songsList").innerText = "Fetching...";
            try {
                const res = await fetch(BASE + "/api/user/history", {
                    headers: { "X-User-Cookie": userCookie }
                });
                const data = await res.json();
                renderItems(data);
            } catch(e) {
                document.getElementById("songsList").innerText = "Failed: " + e.message;
            }
        }

        function renderItems(items) {
            const list = document.getElementById("songsList");
            if (!items || items.length === 0) {
                list.innerHTML = "<p style='color:gray; font-size:12px;'>No items found.</p>";
                return;
            }
            list.innerHTML = items.map(item => `
                <div class="song-item">
                    <img src="${item.thumbnail || 'https://via.placeholder.com/44'}" />
                    <div class="song-info">
                        <h4>${item.title}</h4>
                        <p>${item.subtitle || 'Track'}</p>
                    </div>
                </div>
            `).join('');
        }

        checkSession();
    </script>
</body>
</html>
"""

@app.route("/")
@app.route("/index")
def index():
    return render_template_string(HTML_PAGE)

# 1. Full Home Screen
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

# 2. Album Details
@app.route("/api/album")
def get_album():
    aid = request.args.get("id")
    if not aid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        data = yt.get_album(aid)
        tracks = [parse_item(t) for t in data.get("tracks", []) if parse_item(t)]
        return jsonify({
            "title": data.get("title", ""),
            "year": data.get("year", ""),
            "thumbnail": data.get("thumbnails", [{}])[-1].get("url", ""),
            "tracks": tracks
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. Artist Details
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
            "top_songs": [parse_item(s) for s in data.get("songs", {}).get("results", []) if parse_item(s)],
            "albums": [parse_item(a) for a in data.get("albums", {}).get("results", []) if parse_item(a)]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. Playlist Details
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
            "thumbnail": data.get("thumbnails", [{}])[-1].get("url", ""),
            "tracks": [parse_item(t) for t in data.get("tracks", []) if parse_item(t)]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 5. User Liked Songs (Private)
@app.route("/api/user/liked")
def user_liked_songs():
    yt = get_yt_client()
    try:
        data = yt.get_liked_songs(limit=50)
        tracks = [parse_item(t) for t in data.get("tracks", []) if parse_item(t)]
        return jsonify({"title": "Your Liked Songs", "tracks": tracks})
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

# 6. User Playlists (Private)
@app.route("/api/user/playlists")
def user_library_playlists():
    yt = get_yt_client()
    try:
        playlists = yt.get_library_playlists(limit=50)
        return jsonify([parse_item(p) for p in playlists if parse_item(p)])
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

# 7. User Subscribed Artists (Private)
@app.route("/api/user/artists")
def user_library_artists():
    yt = get_yt_client()
    try:
        artists = yt.get_library_subscriptions(limit=50)
        return jsonify([parse_item(a) for a in artists if parse_item(a)])
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

# 8. User Playback History (Private)
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
