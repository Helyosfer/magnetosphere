"""Sahte bir Kick API'sine karşı uçtan uca testler: python -m unittest test_app"""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import app

REDIRECT = "https://" + "a" * 32 + ".chromiumapp.org/"

# Sahte Kick: kullanıcı kimliği N için token "tok-N", kanal slug'ı USERS[N].
USERS = {1: "yayinci-a", 2: "yayinci-b", 10: "mod-ali", 11: "mod-veli", 99: "trol"}
MODS = {1: {10}, 2: set()}   # mod-ali yalnızca yayinci-a'da moderatör
BANNED = set()               # (broadcaster_id, user_id)


class FakeKick(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, payload):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def uid(self):
        return int(self.headers["Authorization"].removeprefix("Bearer tok-"))

    def body(self):
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        if url.path == "/public/v1/users":
            return self.reply(200, {"data": [{"user_id": self.uid(), "name": USERS[self.uid()]}]})
        if url.path == "/public/v1/channels":
            slug = urllib.parse.parse_qs(url.query)["slug"][0]
            data = [{"broadcaster_user_id": i, "slug": s} for i, s in USERS.items() if s == slug]
            return self.reply(200, {"data": data})
        self.reply(404, {})

    def do_POST(self):
        if self.path == "/oauth/token":
            form = dict(urllib.parse.parse_qsl(self.body().decode()))
            return self.reply(200, {"access_token": "tok-" + form["code"],
                                    "refresh_token": "ref", "expires_in": 3600})
        self.moderate(banned=True)

    def do_DELETE(self):
        self.moderate(banned=False)

    def moderate(self, banned):
        body = json.loads(self.body())
        channel = body["broadcaster_user_id"]
        if self.uid() != channel and self.uid() not in MODS[channel]:
            return self.reply(403, {"message": "Forbidden"})
        key = (channel, body["user_id"])
        BANNED.add(key) if banned else BANNED.discard(key)
        self.reply(200, {"data": {}})


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def call(base, method, path, token=None, body=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with OPENER.open(req) as res:
            return res.status, json.loads(res.read() or b"{}"), res.headers
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), e.headers


class CrossBanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kick, kick_url = serve(FakeKick)
        cls.tmp = tempfile.TemporaryDirectory()
        app.CFG.update(client_id="id", client_secret="secret", kick_id=kick_url, kick_api=kick_url,
                       db=os.path.join(cls.tmp.name, "test.db"), delay=0)
        app.init_db()
        cls.server, cls.base = serve(app.Handler)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.kick.shutdown()
        cls.server.server_close()
        cls.kick.server_close()
        cls.tmp.cleanup()

    def login(self, uid):
        status, _, headers = call(self.base, "GET", "/auth/login?redirect=" + urllib.parse.quote(REDIRECT))
        self.assertEqual(status, 302)
        state = urllib.parse.parse_qs(urllib.parse.urlsplit(headers["Location"]).query)["state"][0]
        status, _, headers = call(self.base, "GET", f"/auth/callback?code={uid}&state={state}")
        self.assertEqual(status, 302)
        self.assertTrue(headers["Location"].startswith(REDIRECT + "#token="))
        return headers["Location"].split("#token=")[1]

    def test_flow(self):
        ali = self.login(10)
        veli = self.login(11)

        # Yabancı bir adrese yönlendirme reddedilir.
        self.assertEqual(call(self.base, "GET", "/auth/login?redirect=https://evil.example/")[0], 400)
        self.assertEqual(call(self.base, "GET", "/me", "yanlis")[0], 401)

        _, team, _ = call(self.base, "POST", "/teams", ali, {"name": "Ekip"})
        tid = team["id"]
        _, info, _ = call(self.base, "GET", f"/teams/{tid}", ali)

        # Üye olmayan ekibi göremez; davet koduyla katılır ama kanal ekleyemez.
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}", veli)[0], 404)
        self.assertEqual(call(self.base, "POST", "/teams/join", veli, {"invite_code": info["invite_code"]})[0], 200)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/channels", veli, {"slug": "yayinci-a"})[0], 403)

        for slug in ("yayinci-a", "Yayinci_B"):
            self.assertEqual(call(self.base, "POST", f"/teams/{tid}/channels", ali, {"slug": slug})[0], 200)

        # Ekip üyesi ve ekipteki yayıncı banlanamaz.
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", ali, {"username": "mod-veli"})[0], 400)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", ali, {"username": "yayinci-b"})[0], 400)
        self.assertEqual(call(self.base, "POST", f"/teams/{tid}/bans", ali, {"username": "yok-boyle-biri"})[0], 404)

        # mod-ali yalnızca yayinci-a'da moderatör: orada tutar, yayinci-b'de reddedilir.
        status, ban, _ = call(self.base, "POST", f"/teams/{tid}/bans", ali,
                              {"username": "@trol", "reason": "spam"})
        self.assertEqual(status, 200)
        by_slug = {r["slug"]: r for r in ban["results"]}
        self.assertEqual(by_slug["yayinci-a"]["status"], "ok")
        self.assertEqual(by_slug["yayinci-a"]["via"], "mod")
        self.assertEqual(by_slug["yayinci-b"]["status"], "failed")
        self.assertEqual(BANNED, {(1, 99)})

        # yayinci-b ekibe katılınca tekrar deneme onun token'ına düşer.
        yayinci_b = self.login(2)
        call(self.base, "POST", "/teams/join", yayinci_b, {"invite_code": info["invite_code"]})
        _, ban, _ = call(self.base, "POST", f"/teams/{tid}/bans/{ban['id']}/retry", ali)
        by_slug = {r["slug"]: r for r in ban["results"]}
        self.assertEqual(by_slug["yayinci-b"]["status"], "ok")
        self.assertEqual(by_slug["yayinci-b"]["via"], "broadcaster")
        self.assertEqual(BANNED, {(1, 99), (2, 99)})

        # Aynı kişiyi yeniden banlamak ikinci bir kayıt açmaz.
        call(self.base, "POST", f"/teams/{tid}/bans", veli, {"username": "trol"})
        _, listing, _ = call(self.base, "GET", f"/teams/{tid}/bans", veli)
        self.assertEqual(len(listing["bans"]), 1)

        # Ban kaldırma her kanalda geri alır.
        _, ban, _ = call(self.base, "DELETE", f"/teams/{tid}/bans/{ban['id']}", ali)
        self.assertIsNotNone(ban["revoked_at"])
        self.assertEqual({r["status"] for r in ban["results"]}, {"unbanned"})
        self.assertEqual(BANNED, set())

        # Çıkarılan üye ekibe erişemez.
        self.assertEqual(call(self.base, "DELETE", f"/teams/{tid}/members/11", ali)[0], 200)
        self.assertEqual(call(self.base, "GET", f"/teams/{tid}/bans", veli)[0], 404)


if __name__ == "__main__":
    unittest.main()
