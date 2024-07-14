from io import BytesIO
import os
import json
import random
import requests
import asyncio
import threading
from colorthief import ColorThief
from base64 import b64encode
from dotenv import load_dotenv, find_dotenv
from flask import Flask, Response, render_template, request
import websockets

load_dotenv(find_dotenv())

PLACEHOLDER_URL = "https://source.unsplash.com/random/300x300/?aerial"
FALLBACK_THEME = "yt.html.j2"

app = Flask(__name__)

shared_data = {}

async def connect_to_websocket():
    uri = "wss://nowapi.tierkun.my.id/receive"  # Replace with your WebSocket server URL

    async with websockets.connect(uri) as websocket:
        print('Connected to WebSocket server')

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    handle_message(data)
                except json.JSONDecodeError as e:
                    print(f'Error parsing JSON: {e}')
        except websockets.ConnectionClosed as e:
            print(f'Disconnected from WebSocket server: {e}')
        except Exception as e:
            print(f'WebSocket error: {e}')

def handle_message(data):
    global shared_data
    shared_data = data

async def websocket_main():
    while True:
        try:
            await connect_to_websocket()
        except Exception as e:
            print(f'Error in WebSocket connection: {e}')
        print('Retrying connection in 5 seconds...')
        await asyncio.sleep(5)

def start_websocket_client():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(websocket_main())
   
def barGen(barCount):
    barCSS = ""
    left = 1
    for i in range(1, barCount + 1):
        anim = random.randint(500, 1000)
        x1 = random.random()
        y1 = random.random() * 2
        x2 = random.random()
        y2 = random.random() * 2
        barCSS += (
            ".bar:nth-child({})  {{ left: {}px; animation-duration: 15s, {}ms; animation-timing-function: ease, cubic-bezier({},{},{},{}); }}".format(
                i, left, anim, x1, y1, x2, y2
            )
        )
        left += 4
    return barCSS

def gradientGen(albumArtURL, color_count):
    colortheif = ColorThief(BytesIO(requests.get(albumArtURL).content))
    palette = colortheif.get_palette(color_count)
    return palette

def getTemplate():
    try:
        file = open("./templates.json", "r")
        templates = json.loads(file.read())
        return templates["templates"][templates["current-theme"]]
    except Exception as e:
        print(f"Failed to load templates.\r\n```{e}```")
        return FALLBACK_THEME

def loadImageB64(url):
    response = requests.get(url)
    return b64encode(response.content).decode("ascii")

def makeSVG(data, background_color, border_color):
    barCount = 84
    contentBar = "".join(["<div class='bar'></div>" for _ in range(barCount)])
    barCSS = barGen(barCount)

    image = loadImageB64(data["thumbnail"])
    barPalette = gradientGen(data["thumbnail"], 4)
    songPalette = gradientGen(data["thumbnail"], 2)

    artistName = data["channel"].replace("&", "&amp;")
    artist = data["artist"]
    songName = data["title"].replace("&", "&amp;")
    songURI = data["url"].replace("&", "&amp;")
    artistURI = data["channelUrl"].replace("&", "&amp;")
    currentStatus = "Currently Playing:"
    duration = data["durationFresh"]
    views = data["views"]

    dataDict = {
        "contentBar": contentBar,
        "barCSS": barCSS,
        "artist": artist,
        "artistName": artistName,
        "songName": songName,
        "songURI": songURI,
        "artistURI": artistURI,
        "image": image,
        "status": currentStatus,
        "background_color": background_color,
        "border_color": border_color,
        "barPalette": barPalette,
        "songPalette": songPalette,
        "duration": duration,   
        "views": views
    }
    print(shared_data)
    return render_template(getTemplate(), **dataDict)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
@app.route('/with_parameters')
def catch_all(path):
    
    background_color = request.args.get('background_color') or "181414"
    border_color = request.args.get('border_color') or "181414"

    svg = makeSVG(shared_data, background_color, border_color)

    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "s-maxage=1"

    return resp

if __name__ == "__main__":
    websocket_thread = threading.Thread(target=start_websocket_client)
    websocket_thread.start()

    app.run(host="0.0.0.0", debug=True, port=os.getenv("PORT") or 5000)
