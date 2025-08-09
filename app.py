from flask import Flask, request, Response, jsonify, abort
import requests
from urllib.parse import urljoin
import json

app = Flask(__name__)

# channels.json থেকে ডাটা লোড
with open('channels.json', 'r') as f:
    channels_data = json.load(f)

base_url = channels_data.get("base_url", "")
logo_url = channels_data.get("logo_url", "")
channels = {ch['id']: ch for ch in channels_data['channels']}

@app.route('/channels')
def list_channels():
    return jsonify([
        {
            "id": c['id'],
            "name": c['name'],
            "categories": c.get('categories', ''),
            "logo_link": logo_url + c.get('logo_link', '')
        }
        for c in channels.values()
    ])

@app.route('/proxy/<channel_id>.m3u8')
def proxy_m3u8(channel_id):
    if channel_id not in channels:
        abort(404, description="Channel not found")
    ch = channels[channel_id]
    original_m3u8_url = urljoin(base_url, ch['m3u8_url'])

    r = requests.get(original_m3u8_url)
    r.raise_for_status()
    content = r.text

    new_lines = []
    for line in content.splitlines():
        if line and not line.startswith("#"):
            new_url = request.host_url.rstrip('/') + f'/proxy/ts/{channel_id}/' + line
            new_lines.append(new_url)
        else:
            new_lines.append(line)

    return Response("\n".join(new_lines), mimetype='application/vnd.apple.mpegurl')

@app.route('/proxy/ts/<channel_id>/<path:ts_filename>')
def proxy_ts(channel_id, ts_filename):
    if channel_id not in channels:
        abort(404, description="Channel not found")

    original_ts_url = urljoin(base_url, f"{channel_id}/{ts_filename}")

    r = requests.get(original_ts_url, stream=True)
    r.raise_for_status()

    def generate():
        for chunk in r.iter_content(chunk_size=8192):
            yield chunk

    return Response(generate(), content_type='video/mp2t')

@app.route('/playlist.m3u')
def playlist():
    lines = ["#EXTM3U"]
    for ch in channels.values():
        url = f"{request.host_url.rstrip('/')}/proxy/{ch['id']}.m3u8"
        logo = logo_url + ch.get("logo_link", "")
        if logo:
            lines.append(f'#EXTINF:-1 tvg-logo="{logo}",{ch["name"]}')
        else:
            lines.append(f'#EXTINF:-1,{ch["name"]}')
        lines.append(url)
    return Response("\n".join(lines), mimetype='application/x-mpegURL')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
