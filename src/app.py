from playwright.sync_api import sync_playwright
import requests
import re
import urllib
import json
import os
import yaml
import time
import datetime
from flask import Flask
from flask import redirect
from flask import render_template

import time

app = Flask(__name__)


datadir = os.environ["DATADIR"]
with open(os.path.join(datadir, "config.yml"), 'r') as file:
    config = yaml.safe_load(file)

class TokenError(Exception):
    pass
class BlockedChannelError(Exception):
    pass

class Tokensniffer:
    def __init__(self, page):
        self.token = []
        self.page = page
    def refresh(self):
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.on("request", self.onRequest)
            page.goto(urllib.parse.urljoin(config["tv_url"] , "/tv/" + self.page + "/"))
            # Wait 10 seconds to ensure cloudflare challenge completes
            time.sleep(10)
            browser.close()
    def onRequest(self, request):
        streamregex = "/([^\_]*).m3u8"
        print(request.url)
        if re.search(streamregex, request.url) != None:
            self.token.append(request.url)
            print("new token: " + request.url)
        else:
            return False

def listChannels():
    res = {}
    channelListRegex = "<a class=\"list-group-item\" href=\"/tv/(.*)/\">(.*)</a>"
    indexHTML = requests.get(config["tv_url"]).text
    for line in indexHTML.splitlines():
        search = re.search(channelListRegex, line)
        if search == None:
            continue
        name = search.group(2)
        url = search.group(1)
        res[name.replace("&amp;", "&")] = url
    return res

def getStreamUrl(page):
    token = Tokensniffer(page)
    token.refresh()
    return token.token

def getStream(page):
    if page not in channels.values():
        raise KeyError()
    if page not in streams.keys():
        streams[page] = getStreamUrl(page)
    if streams[page] == None or streams[page] == []:
        del streams[page]
        raise BlockedChannelError
    r3 = requests.get(streams[page][0])
    if r3.status_code != 200:
        del streams[page]
        raise TokenError("Invalid or Expired token")
    for line in r3.text.splitlines():
        if line.startswith("#"):
            continue
        if "_high" in line:
            return urllib.parse.urljoin(streams[page][0], line)
    return streams[page][0]
#token = Tokensniffer("fox-news-channel-live-stream")
#token.refresh()
channels = listChannels()
streams = {}




@app.route("/channels.m3u")
def fullm3u():
    m3u = "#EXTM3U"
    for i, value in channels.items():
        m3u += "\n#EXTINF:-1 tvg-chno=\"%s\",%s\n%s/channel/%s" % (str(list(channels.keys()).index(i) + 1), i, config["visible_url"], value)
    return(m3u)
@app.route("/channel/<channel>")
def appchannel(channel):
    try:
        res = getStream(channel)
        return redirect(res)
    except TokenError:
        res = getStream(channel)
        return redirect(res)
    except BlockedChannelError:
        return ("Channel is blocked, or Cloudflare verification failed.", 403)
    except KeyError:
        return ("Channel does not exist", 404)

@app.route("/")
def homepage():
    return render_template('index.html', visible_url=config["visible_url"])
