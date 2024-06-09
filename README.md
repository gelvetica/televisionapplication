# Television Application
> Returns HLS stream links for thetvapp.to
## Usage
You can access the m3u at `/channels.m3u` (ex `http://127.0.0.1:8000/channels.m3u`)

If it fails to provide an authenticated stream,
open the original page in a browser on the same network as
televisionapplication, solve any captcha you are given, then try again.
## Setup
### Installation
#### Docker Compose
```
version: "3"
services:
  televisionapplication:
    image: ghcr.io/gelvetica/televisionapplication:main
    container_name: televisionapplication
    restart: 'unless-stopped'
    ports:
      - "8000:8000"
    volumes:
      - /data/televisionapplication:/data
```
#### Linux
**⚠️ Running outside of Docker is not supported**

You will need Python and Git installed before continuing. Depending on your distro, you may need to [setup a Python virtual environment](https://docs.python.org/3.12/library/venv.html).

Clone the repository
```
git clone https://github.com/gelvetica/televisionapplication.git
```
Enter the directory
```
cd televisionapplication
```
Install dependencies
```
pip install -r requirements.txt
playwright install
playwright install-deps
```

You can use the following command to run the app
```
gunicorn -b 0.0.0.0:8000 --timeout 3000 -e DATADIR=/mydirectory/config.yml app:app
```
### Configuration
Your config should be stored in your data directory, as `config.yml`

**Example**

`visible_url` is the url used in the m3u file returned by the server (ex: `visible_url: http://127.0.0.1:8000` returns `http://127.0.0.1:8000/channel/...`)
```
visible_url: "http://127.0.0.1:5000"
tv_url: "https://thetvapp.to"
```
