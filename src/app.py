from playwright.sync_api import sync_playwright
import requests
import re
import urllib.parse
import os
import yaml
from flask import Flask
from flask import request
from flask import redirect
from flask import render_template
from flask import url_for

import time

app = Flask(__name__)

datadir = os.environ["DATADIR"]
with open(os.path.join(datadir, "config.yml"), 'r') as file:
    config = yaml.safe_load(file)


class TokenError(Exception):
    pass


class BlockedChannelError(Exception):
    pass


class TokenSniffer:
    def __init__(self, page):
        self.token = []
        self.page = page

    # noinspection PyTypeChecker
    # Pycharm thinks self.on_request is being incorrectly used with page.goto; Not sure why
    def refresh(self):
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.on("request", self.onRequest)
            page.goto(urllib.parse.urljoin(config["tv_url"] , "/tv/" + self.page + "/"))
            # Wait 10 seconds to ensure cloudflare challenge completes
            time.sleep(10)
            page.on("request", self.on_request)
            page.goto(urllib.parse.urljoin(config["tv_url"], self.page + "/"))
             # Wait 10 seconds to ensure cloudflare challenge completes
            time.sleep(10)
            browser.close()

    def on_request(self, request):
        stream_regex = "/([^_]*).m3u8"
        print(request.url)
        if re.search(stream_regex, request.url) is not None:
            self.token.append(request.url)
            print("new token: " + request.url)
        else:
            return False


def list_channels():
    res = {}
    channel_list_regex = "<a class=\"list-group-item\" href=\"(.*)/\">(.*)</a>"
    index_html = requests.get(config["tv_url"]).text
    for line in index_html.splitlines():
        search = re.search(channel_list_regex, line)
        if search is None:
            continue
        name = search.group(2)
        url = search.group(1)
        res[name.replace("&amp;", "&")] = url
    # event processing
    event_type_regex = "            <h3>(.*)</h3>"
    event_list_regex = "                                            <a class=\"list-group-item\" href=\"(.*)/\">(.*)"
    current_type = None
    current_num = 0
    for line in index_html.splitlines():
        search = re.search(event_type_regex, line)
        if search is None:
            search = re.search(event_list_regex, line)
            if search is None:
                continue
            current_num += 1
            res[current_type + " Event " + str(current_num)] = search.group(1)
            continue
        print(search.group(1))
        current_type = search.group(1)
        current_num = 0

    return res


def get_stream_url(page):
    token = TokenSniffer(page)
    token.refresh()
    return token.token


def get_stream(page):
    if page not in channels.values():
        raise KeyError()
    if page not in streams.keys():
        streams[page] = get_stream_url(page)
    if streams[page] is None or streams[page] is []:
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


events = {}
channels = list_channels()
streams = {}


@app.route("/channels.m3u")
def channels_m3u():
    m3u = "#EXTM3U"
    for i, value in channels.items():
        m3u += ("\n#EXTINF:-1 tvg-chno=\"%s\",%s\n%s" %
                (str(list(channels.keys()).index(i) + 1), i, url_for('appchannel', _external=True, channel=value)))
    return(m3u)

  
@app.route("/channel/<path:channel>")
def app_channel(channel):
    channel = "/" + channel
    try:
        res = get_stream(channel)
        return redirect(res)
    except TokenError:
        res = getStream(channel)
        return redirect(res)
    except BlockedChannelError:
        return "Channel is blocked, or Cloudflare verification failed.", 403

    except KeyError:
        return ("Channel does not exist", 404)

      
@app.route("/")
def homepage():
    return render_template('index.html', m3u_url=url_for('fullm3u', _external=True))
