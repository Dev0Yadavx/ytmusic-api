from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from ytmusicapi import YTMusic
import requests
import json

app = Flask(__name__)
CORS(app)

# Default Guest with India Localization (Hindi/Indian Regional Focus)
yt_guest = YTMusic(language="hi", location="IN")

def get_yt_client():
    raw_cookie = request.headers.get("X-User-Cookie")
    auth_header = request.headers.get("Authorization")

    if raw_cookie:
        try:
            headers_dict = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "hi,en-IN;q=0.9,en;q=0.8",
                "Content-Type": "application/json",
                "X-Origin": "https://music.youtube.com",
                "Cookie": raw_cookie
            }
            return YTMusic(auth=json.dumps(headers_dict), language="hi", location="IN")
        except Exception as e:
            print("Cookie error:", e)

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        try:
            return YTMusic(auth=token, language="hi", location="IN")
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
    <title>YT Music Suite - India Regional & Full Suite (16 Endpoints)</title>
    <style>
        :root {
            --pink-neon: #ff2a85;
            --pink-glow: rgba(255, 42, 133, 0.45);
            --yellow-neon: #ffe600;
            --white-glass: rgba(255, 255, 255, 0.08);
            --white-border: rgba(255, 255, 255, 0.18);
            --bg-dark: #0a040c;
            --text-pure: #ffffff;
            --text-sub: rgba(255, 255, 255, 0.72);
            --green: #4ade80;
            --red: #ff4e45;
            --cyan: #38bdf8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }
        body { background: var(--bg-dark); color: var(--text-pure); min-height: 100vh; padding: 12px; padding-bottom: 90px; }
        .liquid-blob-1 { position: fixed; top: -60px; left: -60px; width: 300px; height: 300px; background: radial-gradient(circle, var(--pink-neon) 0%, transparent 70%); filter: blur(75px); opacity: 0.4; z-index: -1; }
        .liquid-blob-2 { position: fixed; bottom: 30px; right: -50px; width: 300px; height: 300px; background: radial-gradient(circle, var(--yellow-neon) 0%, transparent 70%); filter: blur(80px); opacity: 0.35; z-index: -1; }
        .glass-panel { background: var(--white-glass); backdrop-filter: blur(20px); border: 1px solid var(--white-border); border-radius: 16px; padding: 16px; margin-bottom: 12px; }
        header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
        .title { font-size: 17px; font-weight: 800; display: flex; align-items: center; gap: 6px; }
        .title span.pink { color: var(--pink-neon); }
        .title span.yellow { color: var(--yellow-neon); }
        .nav-tabs { display: flex; gap: 6px; margin-bottom: 12px; overflow-x: auto; scrollbar-width: none; }
        .tab-btn { padding: 8px 14px; border-radius: 18px; font-size: 11px; font-weight: 700; color: var(--text-sub); border: 1px solid var(--white-border); background: var(--white-glass); cursor: pointer; white-space: nowrap; }
        .tab-btn.active { background: linear-gradient(135deg, var(--pink-neon), #ff6097); color: #fff; border-color: transparent; }
        .endpoint-card { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
        .ep-header { display: flex; justify-content: space-between; align-items: center; }
        .ep-tag { font-size: 10px; font-weight: 800; padding: 2px 7px; border-radius: 6px; }
        .tag-public { background: rgba(56, 189, 248, 0.2); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.4); }
        .tag-india { background: rgba(255, 153, 51, 0.2); color: #ff9933; border: 1px solid rgba(255, 153, 51, 0.4); }
        .tag-auth { background: rgba(255, 230, 0, 0.2); color: var(--yellow-neon); border: 1px solid rgba(255, 230, 0, 0.4); }
        .ep-path { background: rgba(0,0,0,0.5); padding: 8px 12px; border-radius: 8px; font-family: monospace; font-size: 11px; color: var(--yellow-neon); display: flex; justify-content: space-between; cursor: pointer; }
        .ep-btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .btn { background: rgba(255,255,255,0.08); border: 1px solid var(--white-border); color: #fff; padding: 8px 0; border-radius: 8px; font-size: 11px; font-weight: 700; text-align: center; cursor: pointer; }
        .btn.run { background: linear-gradient(135deg, rgba(255, 42, 133, 0.4), rgba(255, 230, 0, 0.2)); border-color: var(--pink-neon); }
        .res-box { display: none; background: rgba(0,0,0,0.7); border-radius: 8px; padding: 10px; font-family: monospace; font-size: 11px; color: #ff9ed2; max-height: 220px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
        .code-block { background: rgba(0,0,0,0.7); border: 1px solid var(--white-border); border-radius: 12px; padding: 12px; font-family: monospace; font-size: 11px; color: #a7f3d0; max-height: 480px; overflow-y: auto; white-space: pre; }
        .toast { position: fixed; bottom: 25px; left: 50%; transform: translateX(-50%); background: #fff; color: #000; padding: 8px 18px; border-radius: 20px; font-size: 12px; font-weight: 700; opacity: 0; transition: 0.2s; pointer-events: none; z-index: 9999; }
        .toast.show { opacity: 1; }
    </style>
</head>
<body>
    <div class="liquid-blob-1"></div>
    <div class="liquid-blob-2"></div>

    <div class="glass-panel">
        <header>
            <div class="title"><span class="pink">&#9658; YT</span><span class="yellow">Music Suite (16 Endpoints)</span></div>
            <button class="btn" style="padding:6px 14px; background:linear-gradient(135deg,var(--pink-neon),#ff6097);" onclick="runAllPublic()">Test All 12 Public</button>
        </header>
    </div>

    <div class="nav-tabs">
        <button class="tab-btn active" onclick="switchView('public')">1. Public Endpoints (12)</button>
        <button class="tab-btn" onclick="switchView('auth')">2. User Login Endpoints (4)</button>
        <button class="tab-btn" onclick="switchView('sdk')">3. Complete Kotlin SDK</button>
    </div>

    <!-- 1. Public View -->
    <div id="view-public" style="display:flex; flex-direction:column;">
        <div id="publicList"></div>
    </div>

    <!-- 2. Auth View -->
    <div id="view-auth" style="display:none; flex-direction:column; gap:10px;">
        <div class="glass-panel">
            <h4 style="font-size:13px; color:var(--yellow-neon); margin-bottom:4px;">🔐 User Personal Library (Isolated Per-User)</h4>
            <p style="font-size:11px; color:var(--text-sub); line-height:1.4;">
                User library endpoints ko test karne ke liye request header me <code>X-User-Cookie</code> bhejte hain. Niche cookie daalkar live test karein:
            </p>
            <input type="text" id="userCookieInput" placeholder="Paste user cookie string here..." 
                style="width:100%; margin-top:8px; padding:8px 12px; border-radius:8px; border:1px solid var(--white-border); background:rgba(0,0,0,0.5); color:#fff; font-size:11px; outline:none;">
        </div>
        <div id="authList"></div>
    </div>

    <!-- 3. SDK View -->
    <div id="view-sdk" style="display:none; flex-direction:column; gap:10px;">
        <div class="glass-panel">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <h4 style="font-size:13px;">Complete Android Retrofit Interface</h4>
                <button class="btn" style="padding:4px 12px;" onclick="copySafe(document.getElementById('fullSdkCode').innerText, 'SDK Copied!')">Copy Kotlin SDK</button>
            </div>
            <div class="code-block" id="fullSdkCode"></div>
        </div>
    </div>

    <div class="toast" id="toast">Copied!</div>

    <script>
        const BASE = window.location.origin;

        const PUBLIC_ENDPOINTS = [
            { id: "home", name: "1. Full Home Screen Engine (India)", path: "/api/home/full?country=IN", tag: "INDIA", desc: "Hindi, Punjabi, Regional Quick Picks & Carousels" },
            { id: "charts", name: "2. India Official Top 100 Charts", path: "/api/charts?country=IN", tag: "INDIA", desc: "Top 100 songs, viral videos & top artists in India" },
            { id: "regional", name: "3. Regional Language Hits", path: "/api/regional?lang=bhojpuri", tag: "INDIA", desc: "Browse Bhojpuri, Hindi, Punjabi, Tamil, Telugu, Haryanvi" },
            { id: "album", name: "4. Album Details", path: "/api/album?id=MPREb_uOD2RWVZxhm", tag: "PUBLIC", desc: "Full tracklist, artist, release year and artwork" },
            { id: "artist", name: "5. Artist Details", path: "/api/artist?id=UC56Qctnsu8wAyvzf4Yx6LIw", tag: "PUBLIC", desc: "Arijit Singh / Artist top songs, albums and singles" },
            { id: "playlist", name: "6. Playlist Details", path: "/api/playlist?id=RDCLAK5uy_nbTnrBv4CxZys35IAzhO0-fFCiKD58qzo", tag: "PUBLIC", desc: "All songs in playlist with track count & author" },
            { id: "search", name: "7. Filtered Search", path: "/api/search?q=Bhojpuri%20Song&filter=songs", tag: "PUBLIC", desc: "Search songs, albums, artists, or playlists with spell tolerance" },
            { id: "suggestions", name: "8. Instant Autocomplete", path: "/api/suggestions?q=Arijit", tag: "PUBLIC", desc: "Google/YT Music real-time typing suggestions" },
            { id: "moods", name: "9. Explore Moods & Genres", path: "/api/moods", tag: "PUBLIC", desc: "Party, Romance, Workout, Chill, Devotional categories" },
            { id: "song", name: "10. Song Metadata", path: "/api/song?id=kJQP7kiw5Fk", tag: "PUBLIC", desc: "Length, title, views, author and format details" },
            { id: "watch", name: "11. Radio Queue / Continuous Mix", path: "/api/watch?id=kJQP7kiw5Fk", tag: "PUBLIC", desc: "Automated continuous radio queue based on track" },
            { id: "lyrics", name: "12. Lyrics Summary", path: "/api/lyrics?id=kJQP7kiw5Fk", tag: "PUBLIC", desc: "Lyrics availability and song text snippet" }
        ];

        const AUTH_ENDPOINTS = [
            { id: "liked", name: "13. User Liked Songs", path: "/api/user/liked", desc: "User ke private Google account ke sabhi liked tracks" },
            { id: "user_playlists", name: "14. User Library Playlists", path: "/api/user/playlists", desc: "User ke banaye aur save kiye huye playlists" },
            { id: "user_artists", name: "15. User Subscribed Artists", path: "/api/user/artists", desc: "User ke library me subscribed music channels" },
            { id: "user_history", name: "16. User Playback History", path: "/api/user/history", desc: "User ki recently played Indian & Global song history" }
        ];

        function renderPublic() {
            document.getElementById("publicList").innerHTML = PUBLIC_ENDPOINTS.map(ep => `
                <div class="glass-panel endpoint-card">
                    <div class="ep-header">
                        <span class="ep-tag ${ep.tag === 'INDIA' ? 'tag-india' : 'tag-public'}">${ep.tag}</span>
                        <span id="st-${ep.id}" style="font-size:11px; color:var(--text-sub);">Ready</span>
                    </div>
                    <div>
                        <h4 style="font-size:14px;">${ep.name}</h4>
                        <p style="font-size:11px; color:var(--text-sub);">${ep.desc}</p>
                    </div>
                    <div class="ep-path" onclick="copySafe('${BASE + ep.path}', 'URL Copied!')">
                        <span>${ep.path}</span>
                        <span style="font-size:9px; background:rgba(255,255,255,0.2); padding:2px 5px; border-radius:4px;">COPY</span>
                    </div>
                    <div class="ep-btn-grid">
                        <button class="btn run" onclick="testCall('${ep.id}', '${ep.path}', false)">Send Request</button>
                        <button class="btn" onclick="copySafe('curl \\'${BASE + ep.path}\\'', 'cURL Copied!')">Copy cURL</button>
                    </div>
                    <div class="res-box" id="res-${ep.id}"></div>
                </div>
            `).join('');
        }

        function renderAuth() {
            document.getElementById("authList").innerHTML = AUTH_ENDPOINTS.map(ep => `
                <div class="glass-panel endpoint-card">
                    <div class="ep-header">
                        <span class="ep-tag tag-auth">REQUIRES LOGIN</span>
                        <span id="st-${ep.id}" style="font-size:11px; color:var(--text-sub);">Needs Header</span>
                    </div>
                    <div>
                        <h4 style="font-size:14px;">${ep.name}</h4>
                        <p style="font-size:11px; color:var(--text-sub);">${ep.desc}</p>
                    </div>
                    <div class="ep-path" onclick="copySafe('${BASE + ep.path}', 'URL Copied!')">
                        <span>${ep.path}</span>
                        <span style="font-size:9px; background:rgba(255,255,255,0.2); padding:2px 5px; border-radius:4px;">COPY</span>
                    </div>
                    <div class="ep-btn-grid">
                        <button class="btn run" onclick="testCall('${ep.id}', '${ep.path}', true)">Fetch My Library</button>
                        <button class="btn" onclick="copySafe('curl -H \\'X-User-Cookie: YOUR_COOKIE\\' \\'${BASE + ep.path}\\'', 'cURL Copied!')">Copy Auth cURL</button>
                    </div>
                    <div class="res-box" id="res-${ep.id}"></div>
                </div>
            `).join('');
        }

        async function testCall(id, path, isAuth) {
            const st = document.getElementById("st-" + id);
            const box = document.getElementById("res-" + id);
            st.innerHTML = "<span style='color:var(--yellow-neon);'>Loading...</span>";
            box.style.display = "block";
            box.innerText = "Fetching...";

            const headers = {};
            if (isAuth) {
                const cookieVal = document.getElementById("userCookieInput").value.trim();
                if (cookieVal) headers["X-User-Cookie"] = cookieVal;
            }

            try {
                const res = await fetch(BASE + path, { headers });
                const data = await res.json();
                if (res.ok) {
                    st.innerHTML = "<span style='color:var(--green);'>" + res.status + " OK</span>";
                    box.innerText = JSON.stringify(data, null, 2);
                } else {
                    st.innerHTML = "<span style='color:var(--red);'>" + res.status + " Error</span>";
                    box.innerText = JSON.stringify(data, null, 2);
                }
            } catch(e) {
                st.innerHTML = "<span style='color:var(--red);'>Failed</span>";
                box.innerText = e.message;
            }
        }

        async function runAllPublic() {
            showToast("Testing all 12 public endpoints...");
            for (let ep of PUBLIC_ENDPOINTS) {
                await testCall(ep.id, ep.path, false);
            }
            showToast("Completed all public tests!");
        }

        function switchView(view) {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.getElementById("view-public").style.display = "none";
            document.getElementById("view-auth").style.display = "none";
            document.getElementById("view-sdk").style.display = "none";

            if (view === 'public') {
                document.querySelectorAll(".tab-btn")[0].classList.add("active");
                document.getElementById("view-public").style.display = "flex";
            } else if (view === 'auth') {
                document.querySelectorAll(".tab-btn")[1].classList.add("active");
                document.getElementById("view-auth").style.display = "flex";
            } else {
                document.querySelectorAll(".tab-btn")[2].classList.add("active");
                document.getElementById("view-sdk").style.display = "flex";
            }
        }

        function copySafe(str, msg) {
            const ta = document.createElement("textarea");
            ta.value = str;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            document.body.removeChild(ta);
            showToast(msg);
        }

        function showToast(msg) {
            const t = document.getElementById("toast");
            t.innerText = msg;
            t.classList.add("show");
            setTimeout(() => t.classList.remove("show"), 1800);
        }

        document.getElementById("fullSdkCode").innerText = `// Android Kotlin Retrofit Interface (All 16 Endpoints - India Localized)
package com.ytmusic.client

import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Query

interface YTMusicService {
    // 1. Full Home Screen (India localized)
    @GET("/api/home/full")
    suspend fun getHome(@Query("country") country: String = "IN"): Response<Any>

    // 2. India Official Charts
    @GET("/api/charts")
    suspend fun getCharts(@Query("country") country: String = "IN"): Response<Any>

    // 3. Regional Hits (Bhojpuri, Hindi, Punjabi, Tamil, etc.)
    @GET("/api/regional")
    suspend fun getRegional(@Query("lang") lang: String = "bhojpuri"): Response<List<Any>>

    // 4. Album Details
    @GET("/api/album")
    suspend fun getAlbum(@Query("id") albumBrowseId: String): Response<Any>

    // 5. Artist Details
    @GET("/api/artist")
    suspend fun getArtist(@Query("id") artistBrowseId: String): Response<Any>

    // 6. Playlist Details
    @GET("/api/playlist")
    suspend fun getPlaylist(@Query("id") playlistId: String): Response<Any>

    // 7. Search
    @GET("/api/search")
    suspend fun search(
        @Query("q") query: String,
        @Query("filter") filter: String = "songs"
    ): Response<List<Any>>

    // 8. Autocomplete
    @GET("/api/suggestions")
    suspend fun getSuggestions(@Query("q") query: String): Response<List<String>>

    // 9. Moods & Genres
    @GET("/api/moods")
    suspend fun getMoods(): Response<Any>

    // 10. Song Metadata
    @GET("/api/song")
    suspend fun getSong(@Query("id") videoId: String): Response<Any>

    // 11. Radio Queue
    @GET("/api/watch")
    suspend fun getRadioQueue(@Query("id") videoId: String): Response<Any>

    // 12. Lyrics
    @GET("/api/lyrics")
    suspend fun getLyrics(@Query("id") videoId: String): Response<Any>

    // --- USER LOGIN ENDPOINTS (Pass X-User-Cookie) ---
    // 13. Liked Songs
    @GET("/api/user/liked")
    suspend fun getLikedSongs(@Header("X-User-Cookie") cookie: String): Response<Any>

    // 14. Library Playlists
    @GET("/api/user/playlists")
    suspend fun getUserPlaylists(@Header("X-User-Cookie") cookie: String): Response<Any>

    // 15. Subscribed Artists
    @GET("/api/user/artists")
    suspend fun getUserArtists(@Header("X-User-Cookie") cookie: String): Response<Any>

    // 16. Playback History
    @GET("/api/user/history")
    suspend fun getUserHistory(@Header("X-User-Cookie") cookie: String): Response<Any>
}`;

        renderPublic();
        renderAuth();
    </script>
</body>
</html>
"""

@app.route("/")
@app.route("/index")
def index():
    return render_template_string(HTML_PAGE)

# 1. Full Home Screen Engine (India Localized)
@app.route("/api/home/full")
def full_home_screen():
    country = request.args.get("country", "IN")
    yt = get_yt_client()
    res = {
        "status": "success",
        "region": country,
        "header_chips": [
            {"label": "Bollywood Hits", "params": "ggMPOg1uX1B2MVFqSkVzU1E%3D"},
            {"label": "Bhojpuri Dhamaka", "params": "ggMPOg1uX3ZfM1d1ek9CSlE%3D"},
            {"label": "Punjabi Pop", "params": "ggMPOg1uX254UllOdlJGUUE%3D"},
            {"label": "Devotional & Bhakti", "params": "ggMPOg1uX0d4aXhzTWFUWUE%3D"},
            {"label": "Indian Indie & Lo-Fi", "params": "ggMPOg1uX01ZUWJ4Z3c4M1E%3D"}
        ],
        "sections": []
    }
    try:
        raw_home = yt.get_home(limit=6)
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

    # Indian Charts fallback agar home blank ho
    if not res["sections"]:
        try:
            charts = yt.get_charts(country=country)
            songs = charts.get("songs", {}).get("items", [])
            if songs:
                res["sections"].append({
                    "section_id": "india_trending",
                    "title": "India Top Trending Hits",
                    "layout": "grid_compact",
                    "items": [parse_item(s) for s in songs[:20] if parse_item(s)]
                })
        except Exception:
            pass

    return jsonify(res)

# 2. Charts (India Top 100)
@app.route("/api/charts")
def get_charts():
    country = request.args.get("country", "IN")
    try:
        yt = get_yt_client()
        return jsonify(yt.get_charts(country=country))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. Regional Hits (Bhojpuri, Punjabi, Haryanvi, Hindi, Tamil, Telugu)
@app.route("/api/regional")
def get_regional():
    lang = request.args.get("lang", "bhojpuri").lower().strip()
    query_map = {
        "bhojpuri": "Top Bhojpuri Songs 2026",
        "punjabi": "Latest Punjabi Hits",
        "hindi": "Bollywood Top Hits",
        "haryanvi": "Trending Haryanvi Songs",
        "tamil": "Tamil Viral Hits",
        "telugu": "Telugu Chartbusters"
    }
    q = query_map.get(lang, f"Top {lang} songs")
    try:
        yt = get_yt_client()
        results = yt.search(q, filter="songs", limit=25)
        return jsonify([parse_item(r) for r in results if parse_item(r)])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. Album Details
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
            "artists": data.get("artists", []),
            "tracks": tracks
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 5. Artist Details
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
            "albums": [parse_item(a) for a in data.get("albums", {}).get("results", []) if parse_item(a)],
            "singles": [parse_item(s) for s in data.get("singles", {}).get("results", []) if parse_item(s)]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 6. Playlist Details
@app.route("/api/playlist")
def get_playlist():
    pid = request.args.get("id")
    if not pid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        data = yt.get_playlist(pid, limit=100)
        return jsonify({
            "id": data.get("id", pid),
            "title": data.get("title", ""),
            "author": data.get("author", {}).get("name", ""),
            "thumbnail": data.get("thumbnails", [{}])[-1].get("url", ""),
            "tracks": [parse_item(t) for t in data.get("tracks", []) if parse_item(t)]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 7. Search
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

# 8. Suggestions (Instant typing)
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

# 9. Moods & Genres
@app.route("/api/moods")
def moods():
    try:
        yt = get_yt_client()
        return jsonify(yt.get_mood_categories())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 10. Song Metadata
@app.route("/api/song")
def song_info():
    vid = request.args.get("id")
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        return jsonify(yt.get_song(vid))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 11. Radio Queue
@app.route("/api/watch")
def watch_queue():
    vid = request.args.get("id")
    if not vid: return jsonify({"error": "id required"}), 400
    try:
        yt = get_yt_client()
        return jsonify(yt.get_watch_playlist(videoId=vid, limit=25))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 12. Lyrics
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

# 13. User Liked Songs
@app.route("/api/user/liked")
def user_liked_songs():
    yt = get_yt_client()
    try:
        data = yt.get_liked_songs(limit=50)
        tracks = [parse_item(t) for t in data.get("tracks", []) if parse_item(t)]
        return jsonify({"title": "Aapke Liked Gane", "tracks": tracks})
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

# 14. User Playlists
@app.route("/api/user/playlists")
def user_library_playlists():
    yt = get_yt_client()
    try:
        playlists = yt.get_library_playlists(limit=50)
        return jsonify([parse_item(p) for p in playlists if parse_item(p)])
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

# 15. User Subscribed Artists
@app.route("/api/user/artists")
def user_library_artists():
    yt = get_yt_client()
    try:
        artists = yt.get_library_subscriptions(limit=50)
        return jsonify([parse_item(a) for a in artists if parse_item(a)])
    except Exception as e:
        return jsonify({"error": "Login required", "details": str(e)}), 401

# 16. User Playback History
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
