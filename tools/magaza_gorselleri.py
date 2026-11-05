"""Chrome Web Store görsellerini üretir: python tools/magaza_gorselleri.py [en|tr]

Panel, örnek veriyle (tools/magaza/mock.js) yerel bir sunucudan açılır ve Chromium ile çekilir.
İngilizce görseller store/en/ altına, Türkçeler store/ altına yazılır. Chromium gerekir.
"""
import functools
import http.server
import pathlib
import shutil
import subprocess
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
MAGAZA = ROOT / "tools" / "magaza"

# (sahne, Türkçe dosya, İngilizce dosya, genişlik, yükseklik)
SHOTS = [
    ("banla", "ekran-1-banla.png", "screenshot-1-ban.png", 1280, 800),
    ("liste", "ekran-2-liste.png", "screenshot-2-list.png", 1280, 800),
    ("sira", "ekran-3-sira.png", "screenshot-3-queue.png", 1280, 800),
    ("ekip", "ekran-4-ekip.png", "screenshot-4-team.png", 1280, 800),
    ("sagtik", "ekran-5-sagtik.png", "screenshot-5-right-click.png", 1280, 800),
    ("kucuk", "tanitim-kucuk-440x280.png", "promo-small-440x280.png", 440, 280),
    ("buyuk", "tanitim-buyuk-1400x560.png", "promo-marquee-1400x560.png", 1400, 560),
]


class Handler(http.server.SimpleHTTPRequestHandler):
    """extension/ klasörünü sunar; /magaza/ altını tools/magaza/'dan verir, panel.html'e mock.js ekler."""

    def translate_path(self, path):
        clean = path.split("?", 1)[0]
        if clean.startswith("/magaza/"):
            return str(MAGAZA / clean.removeprefix("/magaza/"))
        return super().translate_path(path)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/panel.html":
            html = (EXT / "panel.html").read_text(encoding="utf-8")
            html = html.replace("<head>", '<head>\n  <script src="/magaza/mock.js"></script>', 1)
            data = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()

    def log_message(self, *args):
        pass


def chromium():
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        if path := shutil.which(name):
            return path
    sys.exit("Chromium bulunamadı.")


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    out_dir = ROOT / "store" / ("en" if lang == "en" else "")
    out_dir.mkdir(parents=True, exist_ok=True)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(EXT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    browser = chromium()

    for shot, tr_name, en_name, width, height in SHOTS:
        target = out_dir / (en_name if lang == "en" else tr_name)
        subprocess.run([
            browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
            "--no-first-run", "--no-default-browser-check", f"--window-size={width},{height}",
            "--virtual-time-budget=6000", f"--screenshot={target}",
            f"{base}/magaza/sahne.html?shot={shot}&lang={lang}",
        ], check=True, capture_output=True)
        print(target.relative_to(ROOT))
    server.shutdown()


if __name__ == "__main__":
    main()
