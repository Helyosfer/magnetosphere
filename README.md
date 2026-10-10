# Magnetosphere

Kick moderasyon ekipleri için ortak ban listesi.

Birden fazla kanalda moderatörlük yapan ekipler, bir trolü her kanalda tek tek banlamak zorunda kalır.
Magnetosphere bunu tek işleme indirir: kullanıcı adını bir kez girersin, ekibin tüm kanallarında
banlanır ve kimin, kimi, neden banladığı ortak listeye yazılır.

Adını, Dünya'yı güneş rüzgârından koruyan manyetik kalkandan alır.

## Özellikler

- **Tek işlemle çoklu kanal banı** — kalıcı ban ya da 7 güne kadar süreli uzaklaştırma.
- **Toplu ban** — bir seferde 100 kullanıcı adına kadar yapıştır, sırayla hepsi banlanır.
- **Ortak liste** — her ban için kim attı, ne zaman, neden ve hangi kanalda tuttu bilgisi.
- **Tekrar dene** — başarısız olan ya da bandan sonra eklenen kanallara banı yeniden uygular.
- **Tek tıkla geri alma** — banı ekibin tüm kanallarında birden kaldırır.
- **Sağ tık kısayolu** — kick.com'da bir kullanıcı adını seç, "Ekibin tüm kanallarında banla".
- **Koruma** — ekip üyeleri ve ekipteki yayıncılar banlanamaz.

## Nasıl çalışır

```
 Chrome extension            Sunucu                    Kick
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│ Moderatörün    │ ───▶ │ Ekipler        │ ───▶ │ Resmi API      │
│ kullandığı     │      │ Ortak liste    │      │ (OAuth 2.1 ve  │
│ panel          │ ◀─── │ Kick oturumları│ ◀─── │ moderasyon)    │
└────────────────┘      └────────────────┘      └────────────────┘
```

- **`extension/`** — Chrome extension'ı (Manifest V3). Ekibin gördüğü arayüz; kendi başına hiçbir
  Kick isteği atmaz.
- **`server/`** — Python sunucusu. Ekipleri, ortak listeyi ve Kick oturumlarını tutar; banları
  Kick'in [resmi API'si](https://docs.kick.com/apis/moderation) üzerinden atar. Ek paket gerektirmez
  (Python 3.10+).

Kick'in OAuth akışı bir Client Secret istediği için sunucu şarttır; Secret extension'ın içine konamaz.

### Yetki modeli

Ban, işlemi yapan moderatörün **kendi Kick yetkisiyle** atılır. Kick reddederse ve o kanalın
yayıncısı da ekibe katılmışsa, yayıncının yetkisiyle yeniden denenir.

Sonuçları:

- Bir moderatör, mod olmadığı ve yayıncısı ekipte olmayan bir kanalda ban atamaz; o kanal listede ✗ görünür.
- Bir yayıncının ekibe katılması, ekipteki herkese o kanalda ban yetkisi verir.
- Kanal ekleme, kanal kaldırma ve üye çıkarma yalnızca ekip sahibine açıktır.

## Kurulum

### 1. Kick uygulaması

[kick.com/settings/developer](https://kick.com/settings/developer) adresinden bir uygulama oluştur
(hesapta iki adımlı doğrulama açık olmalı).

| Alan | Değer |
|---|---|
| Redirect URL | `http://localhost:8787/auth/callback` |
| Scopes | Read user information, Read channel information, Execute moderation actions for moderators |

### 2. Sunucu

```bash
cd server
cp .env.example .env
```

`.env` dosyasına Kick'in verdiği Client ID ve Client Secret'ı yaz, sonra sunucuyu başlat:

```bash
python app.py
```

Sunucu `http://localhost:8787` adresinde dinler.

### 3. Extension

1. Chrome'da `chrome://extensions` sayfasını aç ve **Geliştirici modu**'nu etkinleştir.
2. **Paketlenmemiş öğe yükle** ile `extension` klasörünü seç.
3. Magnetosphere simgesine tıkla, sunucu adresini gir ve **Kick ile giriş yap**'a bas.

## Kullanım

1. Bir kişi ekibi oluşturur, **Ekip** sekmesinden kanalları ekler ve davet kodunu modlarla paylaşır.
2. Modlar extension'ı kurar, Kick ile giriş yapar ve davet koduyla ekibe katılır.
3. **Banla** sekmesine kullanıcı adları girilir (alt alta, virgülle ya da boşlukla ayrılmış).
4. **Liste** sekmesi ortak listeyi ve her kanaldaki sonucu gösterir.

## Ayarlar

`server/.env` dosyasından okunur.

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `KICK_CLIENT_ID` | — | Kick uygulamasının Client ID'si |
| `KICK_CLIENT_SECRET` | — | Kick uygulamasının Client Secret'ı |
| `PUBLIC_URL` | `http://localhost:8787` | Sunucunun dışarıdan erişilen adresi. Kick'teki Redirect URL `{PUBLIC_URL}/auth/callback` olmalı |
| `HOST` | `127.0.0.1` | Dinlenecek arayüz |
| `PORT` | `8787` | Dinlenecek port |
| `DB_PATH` | `server/crossban.db` | SQLite veritabanının yolu |
| `ALLOWED_EXTENSION_IDS` | boş (hepsi) | Girişe izin verilen extension kimlikleri, virgülle ayrılmış |
| `BAN_DELAY_SECONDS` | `0.4` | Kanallar arası bekleme; Kick'in istek sınırına takılmamak için |

## Test

```bash
cd server
python -m unittest test_app
```

Testler sahte bir Kick API'sine karşı uçtan uca çalışır; gerçek Kick'e istek atmaz.

## Güvenlik

- `server/.env` ve `server/crossban.db` gizlidir ve repoya girmez (`.gitignore`). Veritabanı, ekip
  üyelerinin Kick tokenlarını içerir.
- Tokenlar şu an veritabanında **düz metin** durur. Sunucuyu internete açmadan önce şifrelenmeleri gerekir.
- Sunucu internete yalnızca HTTPS arkasında açılmalıdır.
- Extension oturumları şu an süresiz geçerlidir.

## Durum ve yol haritası

Çalışan ilk sürüm. Gerçek Kick üzerinde doğrulananlar: giriş, hem yayıncı hem moderatör yetkisiyle
ban, ban kaldırma ve çok kanallı toplu ban.

Yayına almadan önce yapılacaklar:

- [ ] Tokenların veritabanında şifrelenmesi
- [ ] Oturumlara süre ve yenileme
- [ ] Extension'ın sabit kimliğe ve varsayılan sunucu adresine bağlanması
- [ ] Sunucunun servis olarak çalışması ve veritabanı yedeği
- [ ] Extension simgesi

## Bilinen sınırlar

- Kullanıcı adı, Kick'in kanal adresi kuralıyla aranır (küçük harf, `_` yerine `-`).
- Kanallar ekibe elle eklenir; resmi API "moderatörü olduğum kanallar" listesini vermiyor.
- Süreli banlar süresi dolduktan sonra da listede aktif görünür.
