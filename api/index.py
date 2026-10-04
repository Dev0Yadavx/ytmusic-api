from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from ytmusicapi import YTMusic
import requests
import json
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

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>YT Music Suite - Vercel Live</title>
    <style>
        :root {
            --pink-neon: #ff2a85;
            --pink-glow: rgba(255, 42, 133, 0.45);
            --yellow-neon: #ffe600;
            --yellow-glow: rgba(255, 230, 0, 0.4);
            --white-glass: rgba(255, 255, 255, 0.1);
            --white-border: rgba(255, 255, 255, 0.22);
            --bg-dark: #0a040c;
            --text-pure: #ffffff;
            --text-sub: rgba(255, 255, 255, 0.72);
            --green: #4ade80;
            --red: #ff4e45;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background: var(--bg-dark); color: var(--text-pure); min-height: 100vh; padding-bottom: 110px; overflow-x: hidden; position: relative; }
        .liquid-blob-1 { position: fixed; top: -80px; left: -60px; width: 340px; height: 340px; background: radial-gradient(circle, var(--pink-neon) 0%, transparent 70%); filter: blur(80px); opacity: 0.55; z-index: -1; animation: floatPink 8s infinite alternate ease-in-out; }
        .liquid-blob-2 { position: fixed; bottom: 40px; right: -60px; width: 320px; height: 320px; background: radial-gradient(circle, var(--yellow-neon) 0%, transparent 70%); filter: blur(85px); opacity: 0.45; z-index: -1; animation: floatYellow 10s infinite alternate ease-in-out; }
        @keyframes floatPink { 0% { transform: translateY(0px) scale(1); } 100% { transform: translateY(70px) scale(1.15); } }
        @keyframes floatYellow { 0% { transform: translateY(0px) scale(1); } 100% { transform: translateY(-70px) scale(1.2); } }
        .glass-panel { background: var(--white-glass); backdrop-filter: blur(25px) saturate(180%); -webkit-backdrop-filter: blur(25px) saturate(180%); border: 1px solid var(--white-border); border-radius: 18px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), inset 0 1px 2px rgba(255, 255, 255, 0.2); }
        header { position: sticky; top: 10px; margin: 0 14px 14px; padding: 12px 18px; display: flex; justify-content: space-between; align-items: center; z-index: 100; flex-wrap: wrap; gap: 8px; }
        .brand-title { font-size: 17px; font-weight: 800; display: flex; align-items: center; gap: 6px; }
        .brand-title span.pink { color: var(--pink-neon); text-shadow: 0 0 12px var(--pink-glow); }
        .brand-title span.yellow { color: var(--yellow-neon); text-shadow: 0 0 10px var(--yellow-glow); }
        .btn-action-all { background: linear-gradient(135deg, var(--pink-neon), #ff6097); color: #fff; border: none; padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; cursor: pointer; box-shadow: 0 3px 12px var(--pink-glow); }
        .btn-action-all:active { transform: scale(0.95); }
        .nav-tabs { display: flex; gap: 8px; margin: 0 14px 14px; overflow-x: auto; scrollbar-width: none; }
        .nav-tabs::-webkit-scrollbar { display: none; }
        .tab-btn { padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; color: var(--text-sub); border: 1px solid var(--white-border); background: var(--white-glass); cursor: pointer; white-space: nowrap; transition: 0.2s; }
        .tab-btn.active { background: linear-gradient(135deg, var(--pink-neon), #ff6097); color: #fff; border-color: transparent; box-shadow: 0 4px 15px var(--pink-glow); }
        .app-content { padding: 0 14px; display: flex; flex-direction: column; gap: 14px; }
        .banner-card { padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; background: linear-gradient(135deg, rgba(255, 42, 133, 0.15), rgba(255, 230, 0, 0.1)); border-color: rgba(255, 255, 255, 0.35); flex-wrap: wrap; gap: 10px; }
        .endpoint-card { padding: 16px; display: flex; flex-direction: column; gap: 10px; }
        .ep-top-row { display: flex; justify-content: space-between; align-items: center; }
        .ep-badge { background: rgba(255, 230, 0, 0.2); color: var(--yellow-neon); border: 1px solid rgba(255, 230, 0, 0.4); font-size: 10px; font-weight: 800; padding: 2px 7px; border-radius: 6px; }
        .ep-status { font-size: 11px; color: var(--text-sub); font-weight: 600; }
        .ep-details h3 { font-size: 15px; font-weight: 700; color: #fff; }
        .ep-details p { font-size: 12px; color: var(--text-sub); margin-top: 2px; }
        .tap-copy-path { background: rgba(0, 0, 0, 0.45); border: 1px dashed rgba(255, 255, 255, 0.3); border-radius: 10px; padding: 9px 12px; font-family: monospace; font-size: 11px; color: var(--yellow-neon); display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
        .tap-copy-path:active { background: rgba(255, 42, 133, 0.3); border-color: var(--pink-neon); transform: scale(0.98); }
        .copy-icon-label { font-size: 9px; background: rgba(255, 255, 255, 0.15); color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: 700; }
        .ep-action-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .glass-btn { background: rgba(255, 255, 255, 0.08); border: 1px solid var(--white-border); color: #fff; padding: 8px 0; border-radius: 10px; font-size: 11px; font-weight: 700; text-align: center; cursor: pointer; transition: 0.2s; }
        .glass-btn:active { background: var(--yellow-neon); color: #000; transform: scale(0.95); }
        .glass-btn.run { background: linear-gradient(135deg, rgba(255, 42, 133, 0.35), rgba(255, 230, 0, 0.25)); border-color: var(--pink-neon); }
        .response-box { display: none; background: rgba(0, 0, 0, 0.65); border-radius: 10px; padding: 10px; max-height: 180px; overflow-y: auto; font-family: monospace; font-size: 11px; color: #ff9ed2; white-space: pre-wrap; word-break: break-all; border: 1px solid rgba(255, 255, 255, 0.15); cursor: pointer; }
        .code-block { background: rgba(0, 0, 0, 0.7); border: 1px solid var(--white-border); border-radius: 12px; padding: 12px; font-family: monospace; font-size: 11px; color: #a7f3d0; max-height: 480px; overflow-y: auto; white-space: pre; }
        .live-player { position: fixed; bottom: 0; left: 0; right: 0; background: rgba(14, 8, 16, 0.95); backdrop-filter: blur(15px); border-top: 1px solid var(--white-border); padding: 8px 16px; display: flex; align-items: center; justify-content: space-between; z-index: 1000; }
        .live-player audio { height: 32px; width: 250px; outline: none; }
        .toast { position: fixed; bottom: 45px; left: 50%; transform: translateX(-50%) translateY(100px); background: #fff; color: #000; padding: 8px 20px; border-radius: 30px; font-size: 12px; font-weight: 700; box-shadow: 0 10px 25px rgba(0,0,0,0.5); opacity: 0; transition: all 0.3s cubic-bezier(0.68, -0.55, 0.27, 1.55); z-index: 9999; pointer-events: none; }
        .toast.show { transform: translateX(-50%) translateY(0); opacity: 1; }
    </style>
</head>
<body>
    <div class="liquid-blob-1"></div>
    <div class="liquid-blob-2"></div>
    <header class="glass-panel">
        <div class="brand-title"><span class="pink">&#9658; YT</span><span class="yellow">Music Suite</span></div>
        <button class="btn-action-all" onclick="runAllEndpoints()">&#9654; Test All</button>
    </header>
    <div class="nav-tabs">
        <button class="tab-btn active" onclick="switchTab('endpoints')">API Playground</button>
        <button class="tab-btn" onclick="switchTab('web')">Web JS SDK</button>
        <button class="tab-btn" onclick="switchTab('android')">Android Kotlin SDK</button>
    </div>
    <div class="app-content">
        <div id="view-endpoints" style="display:flex; flex-direction:column; gap:14px;">
            <div class="glass-panel banner-card">
                <div>
                    <h4 style="font-size:13px;">Vercel Serverless Ready</h4>
                    <p style="font-size:11px; color:var(--text-sub);">Tap any endpoint path to copy URL</p>
                </div>
                <button class="glass-btn" style="padding:6px 14px;" onclick="copyAllUrls()">Copy All URLs</button>
            </div>
            <div id="endpointsList" style="display:flex; flex-direction:column; gap:14px;"></div>
        </div>
        <div id="view-web" style="display:none; flex-direction:column; gap:12px;">
            <div class="glass-panel banner-card">
                <div><h4 style="font-size:13px;">Web SDK</h4><p style="font-size:11px; color:var(--text-sub);">Frontend ES6 Module</p></div>
                <button class="glass-btn" style="padding:6px 14px;" onclick="copyCode('webSdkCode', 'Web JS SDK Copied!')">Copy SDK</button>
            </div>
            <div class="code-block" id="webSdkCode"></div>
        </div>
        <div id="view-android" style="display:none; flex-direction:column; gap:12px;">
            <div class="glass-panel banner-card">
                <div><h4 style="font-size:13px;">Android Retrofit SDK</h4><p style="font-size:11px; color:var(--text-sub);">Kotlin Models & Coroutines</p></div>
                <button class="glass-btn" style="padding:6px 14px;" onclick="copyCode('androidSdkCode', 'Android Kotlin SDK Copied!')">Copy SDK</button>
            </div>
            <div class="code-block" id="androidSdkCode"></div>
        </div>
    </div>
    <div class="live-player">
        <div style="font-size:12px; color:var(--text-pure);" id="nowPlayingText">Ready for Playback</div>
        <audio id="globalAudio" controls autoplay></audio>
    </div>
    <div id="toast" class="toast">Copied!</div>
    <script>
        const BASE = window.location.origin;
        const ENDPOINTS = [
            { id: "home_full", name: "Full Home Screen Engine", path: "/api/home/full?country=IN", badge: "GET", desc: "Quick Picks, Carousels, Trending Videos & Artists" },
            { id: "charts", name: "India Charts & Top 100", path: "/api/charts?country=IN", badge: "GET", desc: "Official viral music and top 100 songs in India" },
            { id: "search", name: "Search Songs & Remixes", path: "/api/search?q=Bhojpuri%20Song&filter=songs", badge: "GET", desc: "Songs search with spelling tolerance" },
            { id: "suggestions", name: "Instant Autocomplete", path: "/api/suggestions?q=Arijit", badge: "GET", desc: "Real-time search suggestions" },
            { id: "moods", name: "Explore Moods & Genres", path: "/api/moods", badge: "GET", desc: "Browse categories like Chill, Workout, Party, Romance" },
            { id: "song", name: "Song Metadata", path: "/api/song?id=kJQP7kiw5Fk", badge: "GET", desc: "Length, title, views, author and audio formats" },
            { id: "watch", name: "Radio Queue / Continuous Mix", path: "/api/watch?id=kJQP7kiw5Fk", badge: "GET", desc: "Automated continuous radio queue based on track" },
            { id: "lyrics", name: "Lyrics Summary", path: "/api/lyrics?id=kJQP7kiw5Fk", badge: "GET", desc: "Lyrics availability and summary snippet" },
            { id: "stream", name: "Audio Stream URL Resolver", path: "/api/stream?id=kJQP7kiw5Fk", badge: "GET", desc: "Direct audio playback URL" },
            { id: "refresh", name: "Session Cache Refresh", path: "/api/refresh", badge: "POST", desc: "Flushes session cache and resets connection" }
        ];

        function renderCards() {
            document.getElementById("endpointsList").innerHTML = ENDPOINTS.map((ep, idx) => `
                <div class="glass-panel endpoint-card" id="card-${ep.id}">
                    <div class="ep-top-row">
                        <span class="ep-badge">${ep.badge}</span>
                        <span class="ep-status" id="status-${ep.id}">Ready</span>
                    </div>
                    <div class="ep-details"><h3>${ep.name}</h3><p>${ep.desc}</p></div>
                    <div class="tap-copy-path" onclick="copySafe('${BASE + ep.path}', 'Endpoint URL Copied!')">
                        <span>${ep.path}</span><span class="copy-icon-label">TAP TO COPY</span>
                    </div>
                    <div class="ep-action-grid">
                        <button class="glass-btn run" onclick="testEndpoint(${idx})">Send Request</button>
                        <button class="glass-btn" onclick="copySafe('curl -X ${ep.badge} \\"${BASE + ep.path}\\"', 'cURL Copied!')">Copy cURL</button>
                    </div>
                    <div class="response-box" id="res-${ep.id}"></div>
                </div>
            `).join('');
        }

        async function testEndpoint(idx) {
            const ep = ENDPOINTS[idx];
            const status = document.getElementById(`status-${ep.id}`);
            const resBox = document.getElementById(`res-${ep.id}`);
            status.innerHTML = `<span style="color:var(--yellow-neon);">Testing...</span>`;
            resBox.style.display = "block";
            resBox.innerText = "Loading...";
            const t0 = performance.now();
            try {
                const res = await fetch(`${BASE}${ep.path}`, { method: ep.badge });
                const time = Math.round(performance.now() - t0);
                if (res.ok) {
                    const data = await res.json();
                    status.innerHTML = `<span style="color:var(--green);">${res.status} OK (${time}ms)</span>`;
                    resBox.innerText = JSON.stringify(data, null, 2);
                    showToast(`${ep.name} 200 OK`);
                    resBox.onclick = () => copySafe(resBox.innerText, "JSON Response Copied!");
                    if (ep.id === 'stream' && data.stream_url) {
                        const audio = document.getElementById('globalAudio');
                        audio.src = data.stream_url;
                        document.getElementById('nowPlayingText').innerText = `Playing: ${data.videoId}`;
                        audio.play();
                    }
                    return true;
                } else {
                    status.innerHTML = `<span style="color:var(--red);">${res.status} Error</span>`;
                    resBox.innerText = await res.text();
                    return false;
                }
            } catch(e) {
                status.innerHTML = `<span style="color:var(--red);">Fail</span>`;
                resBox.innerText = e.message;
                return false;
            }
        }

        async function runAllEndpoints() {
            showToast("Testing all endpoints...");
            for(let i=0; i<ENDPOINTS.length; i++) await testEndpoint(i);
            showToast("All tests completed!");
        }

        function copyAllUrls() {
            copySafe(ENDPOINTS.map(e => `${e.badge} ${BASE}${e.path}`).join('\n'), "All URLs Copied!");
        }

        function copyCode(id, msg) { copySafe(document.getElementById(id).innerText, msg); }

        function copySafe(str, msg) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(str).then(() => showToast(msg)).catch(() => fallbackCopy(str, msg));
            } else { fallbackCopy(str, msg); }
        }

        function fallbackCopy(str, msg) {
            const ta = document.createElement("textarea");
            ta.value = str; ta.setAttribute("readonly", "");
            ta.style.position = "absolute"; ta.style.left = "-9999px";
            document.body.appendChild(ta); ta.select();
            try { document.execCommand("copy"); showToast(msg); } catch(e) { prompt("Copy manually:", str); }
            document.body.removeChild(ta);
        }

        function showToast(text) {
            const t = document.getElementById("toast");
            t.innerText = text; t.classList.add("show");
            setTimeout(() => t.classList.remove("show"), 2000);
        }

        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            ['endpoints', 'web', 'android'].forEach(v => document.getElementById(`view-${v}`).style.display = 'none');
            if(tab === 'endpoints') { document.querySelectorAll('.tab-btn')[0].classList.add('active'); document.getElementById('view-endpoints').style.display = 'flex'; }
            else if(tab === 'web') { document.querySelectorAll('.tab-btn')[1].classList.add('active'); document.getElementById('view-web').style.display = 'flex'; }
            else { document.querySelectorAll('.tab-btn')[2].classList.add('active'); document.getElementById('view-android').style.display = 'flex'; }
        }

        document.getElementById("webSdkCode").innerText = `// Universal Web SDK (ES6)
export class YTMusicClient {
    constructor(baseURL = "${BASE}") { this.baseURL = baseURL.replace(/\\/$/, ""); }
    async _get(path) {
        const res = await fetch(\`\${this.baseURL}\${path}\`);
        if (!res.ok) throw new Error(\`HTTP \${res.status}\`);
        return await res.json();
    }
    getFullHomeScreen(country = "IN") { return this._get(\`/api/home/full?country=\${country}\`); }
    getCharts(country = "IN") { return this._get(\`/api/charts?country=\${country}\`); }
    search(query, filter = "songs") { return this._get(\`/api/search?q=\${encodeURIComponent(query)}&filter=\${filter}\`); }
    getSuggestions(query) { return this._get(\`/api/suggestions?q=\${encodeURIComponent(query)}\`); }
    getStream(videoId) { return this._get(\`/api/stream?id=\${videoId}\`); }
}`;

        document.getElementById("androidSdkCode").innerText = `// Android Kotlin Retrofit Client
package com.ytmusic.client
import retrofit2.http.GET
import retrofit2.http.Query
import retrofit2.Response

interface YTMusicService {
    @GET("/api/home/full")
    suspend fun getFullHomeScreen(@Query("country") country: String = "IN"): Response<Any>
    @GET("/api/charts")
    suspend fun getCharts(@Query("country") country: String = "IN"): Response<Any>
    @GET("/api/search")
    suspend fun searchSongs(@Query("q") query: String, @Query("filter") filter: String = "songs"): Response<List<Any>>
    @GET("/api/suggestions")
    suspend fun getSuggestions(@Query("q") query: String): Response<List<String>>
    @GET("/api/stream")
    suspend fun getStreamUrl(@Query("id") videoId: String): Response<Any>
}`;

        renderCards();
    </script>
</body>
</html>
"""

# Root route serving UI
@app.route("/")
@app.route("/index")
def index():
    return render_template_string(HTML_PAGE)

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
            home_response["sections"].append({
                "section_id": "quick_picks",
                "title": "Quick Picks",
                "layout": "grid_compact",
                "items": [parse_item(s) for s in songs[:20] if parse_item(s)]
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

# 9. Serverless-Safe Audio Stream Resolver
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

# 10. Cache Refresh
@app.route("/api/refresh", methods=["POST", "GET"])
def refresh_session():
    global yt
    yt = YTMusic()
    return jsonify({"status": "success", "message": "Guest session refreshed"})

# Vercel Serverless Entry Point
# (Vercel looks for 'app' directly)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
