from playwright.sync_api import sync_playwright
from playwright.sync_api import expect
import requests
import re
import urllib
import json
import os
import yaml
import time
import datetime
from flask import Flask
from flask import request
from flask import redirect
from flask import render_template
from flask import url_for
from flask import send_from_directory

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
            # my thetvapp.to disstrack:
            # thetvapp,
            # you suck
            # i rock
            # you break my app
            # i cry
            # i fix it
            # you break it again bc you actually suck i dont like you
            # get off my github your site has Error Code: 102630
            # please fix it im trying to telly
            expect(page.locator(".col-lg-8")).to_be_enabled()
            page.locator(".col-lg-8").click()
            expect(page.locator(".jw-state-playing")).to_be_enabled()
            browser.close()
    def onRequest(self, request):
        streamregex = r"/[^_]*.m3u8\?"
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
    if "override_playlist" in config:
        if config["override_playlist"] == True:
            return send_from_directory(datadir, "channels.m3u")
    m3u = "#EXTM3U"
    for i, value in channels.items():
        m3u += ("\n#EXTINF:-1 tvg-chno=\"%s\",%s\n%s" %
                (str(list(channels.keys()).index(i) + 1), i, url_for('appchannel', _external=True, channel=value)))
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
    return render_template('index.html', m3u_url=url_for('fullm3u', _external=True))


#@app.route("/buildm3u")
#def wtf():
#    m3u = "#EXTM3U"
#    for name, link in channels.items():
#        html = requests.get(urllib.parse.urljoin(config["tv_url"] , "/tv/" + link + "/")).text.splitlines()
#        for line in html:
#          search = re.search(r"<div id=\"get-m3u8-link\" data=\"/token/(.*)\"></div>", line)
#            if search == None:
#                continue
#            m3u += ("\n#EXTINF:-1 tvg-chno=\"%s\",%s\n%s" %
#                    (str(list(channels.keys()).index(name) + 1), name, "https://load.thetvapp.to/hls/" + search.group(1) + "/index.m3u8"))
#    return m3u




print("""
:3 if something isnt working, please shoot a message to
   the discord channel at https://discord.gg/mc4WaSApvS
""")