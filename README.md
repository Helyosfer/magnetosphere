# Magnetosphere

Kick moderasyon ekipleri için ortak ban listesi.

Birden fazla kanalda moderatörlük yapan ekipler, bir trolü ya da spam botunu her kanalda tek tek
banlamak zorunda kalır. Magnetosphere bunu tek işleme indirir: kullanıcı adını bir kez girersin (ya da
binlercesini bir dosyadan yüklersin), ekibin tüm kanallarında banlanır ve kimin, kimi, neden banladığı
ortak listeye yazılır.

Adını, Dünya'yı güneş rüzgârından koruyan manyetik kalkandan alır.

## Özellikler

- **Tek işlemle çoklu kanal banı** — kalıcı ban ya da 7 güne kadar süreli uzaklaştırma; kanallara aynı anda uygulanır.
- **Toplu ban ve dosyadan içe aktarma** — nick'leri yapıştır ya da `.txt`, `.csv`, `.json` dosyası yükle (tek seferde 5.000'e kadar). CSV'de yalnızca ilk sütun alınır, başlık satırı atlanır.
- **Arka plan sırası** — uzun listeler sunucuda sıraya alınır; panel ya da tarayıcı kapansa da banlar atılmaya devam eder. İlerleme, bulunamayan adlar ve iptal panelden yönetilir.
- **Kick'in istek sınırına uyum** — istek hızı kendiliğinden ayarlanır; Kick yavaşlatırsa kayıtlar kaybolmaz, sıraya geri döner.
- **Ortak liste** — her ban için kim attı, ne zaman, neden ve hangi kanalda tuttu bilgisi; ad ya da sebebe göre arama.
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
│ panel          │ ◀─── │ Sıra ve işçiler│ ◀─── │ moderasyon)    │
└────────────────┘      └────────────────┘      └────────────────┘
```

- **`extension/`** — Chrome extension'ı (Manifest V3). Ekibin gördüğü arayüz; kendi başına hiçbir
  Kick isteği atmaz ve Kick şifreni ya da token'ını görmez.
- **`server/`** — Python sunucusu (3.10+). Ekipleri, ortak listeyi, sırayı ve Kick oturumlarını tutar;
  banları Kick'in [resmi API'si](https://docs.kick.com/apis/moderation) üzerinden atar.

Kick'in OAuth akışı bir Client Secret istediği için sunucu şarttır; Secret extension'ın içine konamaz.

### Yetki modeli

Ban, işlemi yapan moderatörün **kendi Kick yetkisiyle** atılır. Kick reddederse ve o kanalın
yayıncısı da ekibe katılmışsa, yayıncının yetkisiyle yeniden denenir.

- Bir moderatör, mod olmadığı ve yayıncısı ekipte olmayan bir kanalda ban atamaz; o kanal listede kırmızı görünür.
- Bir yayıncının ekibe katılması, ekipteki herkese o kanalda ban yetkisi verir.
- Kanal ekleme, kanal kaldırma, üye çıkarma ve davet kodunu yenileme yalnızca ekip sahibine açıktır.
- Ekipteki her üye ban atabilir, ban kaldırabilir ve liste yükleyebilir.

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
pip install -r requirements.txt
cp .env.example .env
```

`.env` dosyasını doldur:

- `KICK_CLIENT_ID` ve `KICK_CLIENT_SECRET`: Kick'in verdiği değerler.
- `TOKEN_ENCRYPTION_KEY`: aşağıdaki komutla üretilen anahtar.

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Sonra sunucuyu başlat:

```bash
python app.py
```

Sunucu `http://localhost:8787` adresinde dinler. Eksik bir güvenlik ayarı varsa açılışta uyarı yazar.

### 3. Extension

1. Chrome'da `chrome://extensions` sayfasını aç ve **Geliştirici modu**'nu etkinleştir.
2. **Paketlenmemiş öğe yükle** ile `extension` klasörünü seç.
3. Magnetosphere simgesine tıkla ve **Kick ile giriş yap**'a bas. Sunucu başka bir adresteyse önce
   "Sunucu ayarı"ndan adresi gir.

Extension'ın kimliği `manifest.json` içindeki anahtarla sabitlenmiştir
(`flmfmniipeobbaoahmbdkjnblbegalob`); her bilgisayarda aynı çıkar ve sunucu yalnızca bu kimliği kabul eder.

## Kullanım

1. Bir kişi ekibi oluşturur, **Ekip** sekmesinden kanalları ekler ve davet kodunu modlarla paylaşır.
2. Modlar extension'ı kurar, Kick ile giriş yapar ve davet koduyla ekibe katılır.
3. **Banla** sekmesine kullanıcı adları girilir ya da **Dosyadan yükle** ile liste seçilir.
   10 addan uzun listeler sıraya alınır.
4. **Liste** sekmesi ortak listeyi ve her kanaldaki sonucu gösterir.

## Ayarlar

`server/.env` dosyasından okunur.

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `KICK_CLIENT_ID` | — | Kick uygulamasının Client ID'si |
| `KICK_CLIENT_SECRET` | — | Kick uygulamasının Client Secret'ı |
| `TOKEN_ENCRYPTION_KEY` | boş | Kick tokenlarını veritabanında şifreleyen anahtar. Boşsa tokenlar düz metin kalır |
| `ALLOWED_EXTENSION_IDS` | boş (hepsi) | Giriş yapmasına ve API'yi çağırmasına izin verilen extension kimlikleri, virgülle ayrılmış |
| `PUBLIC_URL` | `http://localhost:8787` | Sunucunun dışarıdan erişilen adresi. Kick'teki Redirect URL `{PUBLIC_URL}/auth/callback` olmalı |
| `HOST` | `127.0.0.1` | Dinlenecek arayüz |
| `PORT` | `8787` | Dinlenecek port |
| `DB_PATH` | `server/crossban.db` | SQLite veritabanının yolu |
| `QUEUE_WORKERS` | `4` | Sırayı aynı anda işleyen işçi sayısı |
| `KICK_REQUESTS_PER_SECOND` | `1` | Kick API'sine başlangıç istek hızı; Kick 429 dönerse kendiliğinden düşer, sorun yoksa yükselir |
| `KICK_REQUESTS_PER_SECOND_MAX` | `5` | İstek hızının üst sınırı |

## Güvenlik

**Neler korunuyor**

- **Kick tokenları şifreli saklanır.** `TOKEN_ENCRYPTION_KEY` tanımlıyken veritabanındaki access ve
  refresh tokenlar Fernet (AES + HMAC) ile şifrelidir; veritabanı dosyası tek başına sızarsa tokenlar okunamaz.
- **Extension oturumları.** Oturum anahtarı veritabanında yalnızca özet (SHA-256) olarak durur,
  30 gün kullanılmazsa geçersiz olur. Çıkış yapmak kullanıcının tüm oturumlarını kapatır.
- **Yalnızca bu extension.** `ALLOWED_EXTENSION_IDS` tanımlıyken başka bir extension ne giriş akışını
  başlatabilir ne de tarayıcıdan API'yi çağırabilir (CORS yalnızca izinli kimliğe açılır).
- **Giriş akışı.** OAuth, PKCE ve tek kullanımlık `state` ile yapılır; oturum yalnızca Chrome'un
  extension'a özel yönlendirme adresine teslim edilir.
- **Davet kodu.** Rastgele 72 bitliktir ve ekip sahibi tarafından yenilenebilir; eski kod anında geçersiz olur.
- **Asgari izin.** Kick'ten yalnızca kullanıcı bilgisi, kanal bilgisi ve ban yetkisi istenir. Extension
  yalnızca `identity`, `storage` ve `contextMenus` izinlerini kullanır; hiçbir siteye içerik betiği enjekte etmez.
- **Sınırlar.** İstek gövdesi 1 MB ile, tek seferde yüklenen liste 5.000 adla sınırlıdır.

**Sunucuyu işleten kişinin sorumlulukları**

- `server/.env` (Client Secret, şifreleme anahtarı) ve `server/crossban.db` gizlidir; `.gitignore`
  ikisini de depo dışında tutar. Şifreleme anahtarı ile veritabanını aynı yedeğe koyma.
- Sunucuyu internete yalnızca HTTPS arkasında aç. `HOST` varsayılan olarak yalnızca yerel makineyi dinler.
- Şifreleme anahtarı kaybolursa veri kaybı olmaz; yalnızca herkesin Kick ile yeniden giriş yapması gerekir.

**Bilinen sınırlar**

- Şifreleme, veritabanı dosyasının sızmasına karşı korur; sunucunun tamamını ele geçiren biri anahtarı da okuyabilir.
- Ekip içinde rol ayrımı yoktur: her üye ban kaldırabilir ve liste yükleyebilir. Ekibe yalnızca güvendiğin kişileri al.
- Bir güvenlik açığı bulursan lütfen herkese açık bir issue yerine depo sahibine özelden bildir.

## Test

```bash
cd server
python -m unittest test_app
```

Testler sahte bir Kick API'sine karşı uçtan uca çalışır; gerçek Kick'e istek atmaz. Giriş, yetki
düşüşü, sıra ve eşzamanlı işçiler ile güvenlik kuralları kapsanır.

## Durum ve yol haritası

Çalışan sürüm. Gerçek Kick üzerinde doğrulananlar: giriş, hem yayıncı hem moderatör yetkisiyle ban,
ban kaldırma ve iki kanalda binlerce hesaplık toplu içe aktarma.

- [x] Tokenların veritabanında şifrelenmesi
- [x] Oturumlara süre
- [x] Extension'ın sabit kimliğe bağlanması
- [x] Extension simgesi
- [ ] Sunucunun internette HTTPS arkasında, servis olarak çalışması ve veritabanı yedeği
- [ ] Sohbeti dinleyip spam botlarını şüpheli kuyruğuna alan otomatik yakalama
- [ ] Ekip içinde roller (yalnızca yetkili üyeler ban kaldırabilsin)
- [ ] Chrome Web Store yayını

## Bilinen sınırlar

- Kullanıcı adı, Kick'in kanal adresi kuralıyla aranır (küçük harf, `_` yerine `-`, en fazla 25 karakter).
- Kanallar ekibe elle eklenir; resmi API "moderatörü olduğum kanallar" listesini vermiyor.
- Süreli banlar süresi dolduktan sonra da listede aktif görünür.
- Hız, Kick'in istek sınırıyla belirlenir: iki kanallı bir ekipte hesap başına yaklaşık bir saniye.
