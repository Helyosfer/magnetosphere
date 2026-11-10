"""Canlı sunucuda Kick tokenlarının şifreli saklandığını, hiçbir gizli değeri göstermeden doğrular.

Sunucuda, veritabanını ve .env dosyasını okuyabilen bir kullanıcıyla çalıştırılır:

    python sifreleme_dogrula.py --sunucu /opt/magnetosphere/app/server --yedek /opt/backups

Rapor yalnızca sayılardan ve evet/hayır sonuçlarından oluşur; anahtar, token, kullanıcı adı ya da
kimlik numarası yazmaz. Bu yüzden çıktısı olduğu gibi paylaşılabilir. Düz metin token bulunursa ya da
anahtar geçersizse çıkış kodu 1 olur.

Neyin ölçüldüğünü herkes bu dosyayı okuyarak görebilir. Çıktının bu dosyadan üretildiğini göstermek için
raporun başında dosyanın SHA-256 özeti yazar; depodaki sürümle karşılaştırılabilir.
Yalnızca standart kütüphane ve sunucunun zaten kullandığı `cryptography` paketi gerekir.
"""
import argparse
import base64
import binascii
import gzip
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

SEALED = "enc:"   # server/app.py'deki önek: şifreli değerler bununla başlar
UYARI = "TOKEN_ENCRYPTION_KEY tanımlı değil"
EN_BUYUK_TARAMA = 50 * 1024 * 1024   # anahtarın kopyası aranırken okunacak en büyük dosya


def env_degerleri(path):
    """server/app.py'deki load_dotenv ile aynı kural: KEY=değer, # ile başlayan satırlar yorum."""
    values = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values.setdefault(key.strip(), value.strip())
    return values


def anahtar_gecerli(key):
    """Fernet anahtarı: URL-güvenli base64 ile yazılmış 32 bayt."""
    try:
        return len(base64.urlsafe_b64decode(key.encode())) == 32
    except (binascii.Error, ValueError):
        return False


COLUMNS = ("access_token", "refresh_token")


def cozulur(cipher, value):
    try:
        cipher.decrypt(value[len(SEALED):].encode())
        return True
    except Exception:
        return False


def token_sayilari(db, cipher=None):
    """users tablosundaki tokenları sayar; değerleri döndürmez.

    Kullanıcı başına: iki sütundan biri bile düz metinse kullanıcı "düz metin" sayılır, şifreli sayılması için
    dolu olan her sütun şifreli olmalı. Ayrıca access_token ve refresh_token sütunları ayrı ayrı sayılır.
    """
    counts = {"kullanici": 0, "sifreli": 0, "duz_metin": 0, "bos": 0}
    columns = {c: {"sifreli": 0, "duz_metin": 0, "bos": 0} for c in COLUMNS}
    if cipher:
        counts["cozulebilen"] = 0
        for c in COLUMNS:
            columns[c]["cozulebilen"] = 0
    for row in db.execute(f"SELECT {', '.join(COLUMNS)} FROM users"):
        counts["kullanici"] += 1
        for column, value in zip(COLUMNS, row):
            kind = "bos" if not value else "sifreli" if value.startswith(SEALED) else "duz_metin"
            columns[column][kind] += 1
            if cipher and kind == "sifreli" and cozulur(cipher, value):
                columns[column]["cozulebilen"] += 1
        if not any(row):
            counts["bos"] += 1   # hesabını silmiş, kaydı başka ekiplerin listesinde kalan kullanıcı
        elif any(value and not value.startswith(SEALED) for value in row):
            counts["duz_metin"] += 1
        else:
            counts["sifreli"] += 1
            if cipher and all(cozulur(cipher, value) for value in row if value):
                counts["cozulebilen"] += 1
    counts["sutunlar"] = columns
    return counts


def yedegi_ac(path):
    """.db ya da .db.gz yedeğini salt okunur açar. Sıkıştırılmış yedek geçici bir dosyaya açılır ve hemen silinir."""
    if not path.endswith(".gz"):
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True), None
    handle, temp = tempfile.mkstemp(suffix=".db")
    with os.fdopen(handle, "wb") as out, gzip.open(path, "rb") as src:
        while chunk := src.read(1 << 20):
            out.write(chunk)
    return sqlite3.connect(f"file:{temp}?mode=ro", uri=True), temp


def anahtar_kopyasi_var(path, key):
    """Dosyanın (sıkıştırılmışsa açılmış hâlinin) içinde anahtarın kendisi geçiyor mu?"""
    try:
        if os.path.getsize(path) > EN_BUYUK_TARAMA:
            return None
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rb") as f:
            return key.encode() in f.read(EN_BUYUK_TARAMA + 1)
    except (OSError, EOFError, gzip.BadGzipFile):
        return None


def yedekleri_tara(dirs, key):
    yedekler, kopyalar, taranamayan = [], 0, 0
    for root in dirs:
        for folder, _, files in os.walk(root):
            for name in sorted(files):
                path = os.path.join(folder, name)
                if key:
                    found = anahtar_kopyasi_var(path, key)
                    kopyalar += found is True
                    taranamayan += found is None
                if not re.search(r"\.db(\.gz)?$", name):
                    continue
                temp = None
                try:
                    db, temp = yedegi_ac(path)
                    counts = token_sayilari(db)
                    db.close()
                except (sqlite3.DatabaseError, OSError, EOFError, gzip.BadGzipFile) as e:
                    counts = {"hata": type(e).__name__}
                finally:
                    if temp:
                        os.remove(temp)
                yedekler.append({"dosya": os.path.relpath(path, root), "tarih": time.strftime(
                    "%Y-%m-%d", time.gmtime(os.path.getmtime(path))), **counts})
    return yedekler, kopyalar, taranamayan


def sunucu_uyarisi(service):
    """Servisin son açılışından beri 'anahtar tanımlı değil' uyarısı basıldı mı? journalctl yoksa None."""
    try:
        since = subprocess.run(["systemctl", "show", "-p", "ActiveEnterTimestamp", "--value", service],
                               capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        log = subprocess.run(["journalctl", "-u", service, "--since", since, "--no-pager", "-o", "cat"],
                             capture_output=True, text=True, timeout=30, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return {"son_acilis": since, "uyari_sayisi": log.count(UYARI)}


def surum(server_dir):
    try:
        with open(os.path.join(server_dir, "app.py"), encoding="utf-8") as f:
            match = re.search(r'^VERSION = "([^"]+)"', f.read(), re.M)
        return match.group(1) if match else None
    except OSError:
        return None


def commit(server_dir):
    try:
        return subprocess.run(["git", "-c", "safe.directory=*", "-C", server_dir, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def rapor(args):
    env = env_degerleri(os.path.join(args.sunucu, ".env"))
    # server/app.py ile aynı öncelik: ortam değişkeni .env'deki değerden önce gelir.
    key = os.environ.get("TOKEN_ENCRYPTION_KEY") or env.get("TOKEN_ENCRYPTION_KEY", "")
    db_path = os.environ.get("DB_PATH") or env.get("DB_PATH") or os.path.join(args.sunucu, "crossban.db")
    cipher = None
    if key and anahtar_gecerli(key):
        from cryptography.fernet import Fernet
        cipher = Fernet(key.encode())

    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    canli = token_sayilari(db, cipher)
    db.close()
    yedekler, kopyalar, taranamayan = yedekleri_tara(args.yedek, key)

    with open(os.path.abspath(__file__), "rb") as f:
        own_hash = hashlib.sha256(f.read()).hexdigest()
    return {
        "rapor_zamani": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "betik_sha256": own_hash,
        "sunucu_surumu": surum(args.sunucu),
        "sunucu_commit": commit(args.sunucu),
        "anahtar": {"tanimli": bool(key), "gecerli_fernet_anahtari": bool(cipher)},
        "sunucu_acilisi": sunucu_uyarisi(args.servis) if args.servis else None,
        "canli_veritabani": canli,
        "yedekler": yedekler,
        "yedeklerde_anahtar_kopyasi": kopyalar if key else None,
        "taranamayan_yedek_dosyasi": taranamayan if key else None,
    }


def basarili(r):
    canli = r["canli_veritabani"]
    return (r["anahtar"]["gecerli_fernet_anahtari"] and canli["duz_metin"] == 0
            and canli.get("cozulebilen") == canli["sifreli"]
            and all(c["duz_metin"] == 0 and c.get("cozulebilen") == c["sifreli"]
                    for c in canli["sutunlar"].values())
            and all(y.get("duz_metin", 0) == 0 and "hata" not in y for y in r["yedekler"])
            and not r["yedeklerde_anahtar_kopyasi"]
            and not (r["sunucu_acilisi"] or {}).get("uyari_sayisi"))


def yazdir(r):
    evet = lambda b: "evet" if b else "HAYIR"
    canli = r["canli_veritabani"]
    print(f"Magnetosphere şifreleme doğrulaması · {r['rapor_zamani']}")
    print(f"Betik SHA-256: {r['betik_sha256']}")
    print(f"Sunucu sürümü: {r['sunucu_surumu'] or '?'} · commit {r['sunucu_commit'] or '?'}")
    print()
    print(f"Anahtar tanımlı:                 {evet(r['anahtar']['tanimli'])}")
    print(f"Geçerli Fernet anahtarı:         {evet(r['anahtar']['gecerli_fernet_anahtari'])}")
    if r["sunucu_acilisi"]:
        print(f"Son açılıştan beri uyarı:        {r['sunucu_acilisi']['uyari_sayisi']}"
              f"  (açılış: {r['sunucu_acilisi']['son_acilis']})")
    print()
    print("Canlı veritabanı")
    print(f"  Kullanıcı:                     {canli['kullanici']}")
    print(f"  Şifreli token:                 {canli['sifreli']}")
    print(f"  Düz metin token:               {canli['duz_metin']}")
    print(f"  Boş (silinmiş hesap):          {canli['bos']}")
    if "cozulebilen" in canli:
        print(f"  Anahtarla çözülebilen:         {canli['cozulebilen']}/{canli['sifreli']}")
    print("  Sütun bazında (şifreli / düz metin / boş / çözülebilen):")
    for column, c in canli["sutunlar"].items():
        print(f"    {column + ':':<28} {c['sifreli']} / {c['duz_metin']} / {c['bos']} / {c.get('cozulebilen', '-')}")
    print()
    print(f"Yedekler ({len(r['yedekler'])} veritabanı yedeği; sütunlar: şifreli/düz metin)")
    for y in r["yedekler"]:
        if "hata" in y:
            print(f"  {y['tarih']}  {y['dosya']}: açılamadı ({y['hata']})")
        else:
            cols = " · ".join(f"{name.split('_')[0]} {c['sifreli']}/{c['duz_metin']}" for name, c in y["sutunlar"].items())
            print(f"  {y['tarih']}  {y['dosya']}: {y['sifreli']} şifreli, {y['duz_metin']} düz metin ({cols})")
    if r["yedeklerde_anahtar_kopyasi"] is not None:
        print(f"  Yedek klasörlerinde anahtarın kopyası: {r['yedeklerde_anahtar_kopyasi']} dosya"
              + (f" ({r['taranamayan_yedek_dosyasi']} dosya taranamadı)" if r["taranamayan_yedek_dosyasi"] else ""))
    print()
    print("SONUÇ: " + ("düz metin token yok, şifreleme çalışıyor" if basarili(r)
                       else "SORUN VAR, yukarıdaki HAYIR ve sıfır olmayan değerlere bak"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sunucu", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"),
                        help="app.py ve .env'nin bulunduğu klasör")
    parser.add_argument("--yedek", action="append", default=[], help="taranacak yedek klasörü (birden çok verilebilir)")
    parser.add_argument("--servis", default="magnetosphere", help="systemd servisinin adı; boş verilirse günlüğe bakılmaz")
    parser.add_argument("--json", action="store_true", help="raporu JSON olarak yaz")
    args = parser.parse_args(argv)
    r = rapor(args)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        yazdir(r)
    return 0 if basarili(r) else 1


if __name__ == "__main__":
    sys.exit(main())
