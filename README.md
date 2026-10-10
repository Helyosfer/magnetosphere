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
- **Ekip yönetimi** — davet koduyla katılma, kodu yenileme, üye çıkarma ve ekibi tümüyle silme.

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
- Kanal ekleme, kanal kaldırma, üye çıkarma, davet kodunu yenileme ve ekibi silme yalnızca ekip sahibine açıktır.
- Ekip silinince üyelikler, kanallar ve ortak liste de silinir; Kick'teki banlar yerinde kalır.
- Ekipteki her üye ban atabilir, ban kaldırabilir ve liste yükleyebilir.

## Kurulum

Magnetosphere kendi sunucunda çalışacak şekilde tasarlanmıştır: her ekip (ya da topluluk) kendi Kick
uygulamasını ve kendi sunucusunu kurar. Depodaki extension'ın varsayılan sunucusu yazarın kendi
sunucusudur (`magnetosphere.helyosfer.me`); orada ekip oluşturma kapalıdır, yalnızca davet koduyla
katılınabilir. Kendi ekibin için aşağıdaki adımlarla kendi sunucunu kur.

Önce kendi bilgisayarında denemek için 1–3. adımlar yeterlidir; herkesin kullanacağı kalıcı kurulum için
aşağıdaki "İnternete açmak" bölümüne geç.

### 1. Kick uygulaması

[kick.com/settings/developer](https://kick.com/settings/developer) adresinden bir uygulama oluştur
(hesapta iki adımlı doğrulama açık olmalı). Uygulama adında boşluk kullanılamaz.

| Alan | Değer |
|---|---|
| Redirect URL | `http://localhost:8787/auth/callback` (yerel deneme) ya da `https://<alan-adın>/auth/callback` |
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
3. Magnetosphere simgesine tıkla, "Sunucu ayarı"na kendi sunucunun adresini yaz
   (yerel deneme için `http://localhost:8787`) ve **Kick ile giriş yap**'a bas.

Extension Chromium tabanlı tarayıcılarda (Chrome, Edge, Brave) çalışır; Firefox desteklenmez.

Ekibindeki herkesin adresi elle girmesini istemiyorsan `extension/panel.js` içindeki `DEFAULT_SERVER`
değerini kendi adresinle değiştirip klasörü öyle dağıt.

Elle yüklenen extension'ın kimliği `manifest.json` içindeki anahtarla sabitlenmiştir
(`flmfmniipeobbaoahmbdkjnblbegalob`); her bilgisayarda aynı çıkar. Sunucu yalnızca
`ALLOWED_EXTENSION_IDS` listesindeki kimlikleri kabul eder. Extension'ı Chrome Web Store'da yayınlarsan
mağaza `key` alanını kabul etmez ve kendi kimliğini atar; o kimliği de listeye eklemen gerekir.

### İnternete açmak

Ekibin kullanacağı kurulumda sunucu sürekli çalışmalı ve HTTPS arkasında olmalıdır.

1. **Ayarlar.** `.env` içinde `PUBLIC_URL=https://<alan-adın>` yap ve Kick uygulamasındaki Redirect
   URL'i `https://<alan-adın>/auth/callback` olarak güncelle. `HOST=127.0.0.1` kalsın; sunucu dışarıya
   doğrudan açılmaz. Veritabanını kodun dışında tutmak için `DB_PATH` ver.
2. **Ters vekil.** HTTPS'i bir ters vekil sağlar. [Caddy](https://caddyserver.com) ile sertifika
   kendiliğinden alınır:

   ```
   <alan-adın> {
   	reverse_proxy 127.0.0.1:8787
   }
   ```

   Giriş sınırı gerçek istemci adresini `X-Forwarded-For` başlığının son değerinden okur; vekilin bu
   başlığı eklediğinden emin ol (Caddy ve nginx varsayılan ayarla ekler).
3. **Servis.** Sunucuyu yetkisiz bir sistem kullanıcısıyla, systemd servisi olarak çalıştır:

   ```ini
   [Service]
   User=magnetosphere
   WorkingDirectory=/opt/magnetosphere/app/server
   ExecStart=/opt/magnetosphere/venv/bin/python app.py
   Environment=PYTHONUNBUFFERED=1
   Restart=on-failure
   NoNewPrivileges=true
   ProtectSystem=strict
   ReadWritePaths=/opt/magnetosphere/data
   ```

4. **Kimler ekip açabilir.** Sunucun herkese açıksa `ALLOWED_TEAM_CREATORS` ile ekip oluşturmayı
   kendi Kick kullanıcı kimliğinle sınırla; diğerleri davet koduyla katılır.
5. **Yedek.** Veritabanı çalışırken güvenle yedeklenebilir:

   ```bash
   sqlite3 /opt/magnetosphere/data/crossban.db ".backup '/opt/backups/crossban-$(date +%F).db'"
   ```

   `.env` dosyasını bu yedeğin yanına koyma; şifreleme anahtarı ile veritabanı ayrı durmalı.

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
| `ALLOWED_TEAM_CREATORS` | boş (herkes) | Ekip oluşturabilecek Kick kullanıcı kimlikleri, virgülle ayrılmış. Davetle katılmak her durumda açıktır |
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
- **Sınırlar.** İstek gövdesi 1 MB ile, tek seferde yüklenen liste 5.000 adla, bir ekibin sırada
  bekleyen kaydı 20.000 ile sınırlıdır. Aynı adresten 10 dakikada en fazla 30 giriş başlatılabilir.
- **Adil sıra.** Sıra ekipler arasında dönüşümlü işlenir; bir ekibin uzun listesi diğerlerini bekletmez.

**Sunucuyu işleten kişinin sorumlulukları**

- `server/.env` (Client Secret, şifreleme anahtarı) ve `server/crossban.db` gizlidir; `.gitignore`
  ikisini de depo dışında tutar. Şifreleme anahtarı ile veritabanını aynı yedeğe koyma.
- Sunucuyu internete yalnızca HTTPS arkasında aç. `HOST` varsayılan olarak yalnızca yerel makineyi dinler.
- Şifreleme anahtarı kaybolursa veri kaybı olmaz; yalnızca herkesin Kick ile yeniden giriş yapması gerekir.

**Bilinen sınırlar**

- Şifreleme, veritabanı dosyasının sızmasına karşı korur; sunucunun tamamını ele geçiren biri anahtarı da okuyabilir.
- Ekip içinde rol ayrımı yoktur: her üye ban kaldırabilir ve liste yükleyebilir. Ekibe yalnızca güvendiğin kişileri al.
- Sunucuda giriş başlatma dışında genel bir istek sınırı yoktur; gerekiyorsa ters vekilde uygula.
- Bir güvenlik açığı bulursan lütfen herkese açık bir issue yerine `destek@helyosfer.me` adresine bildir.

## Test

```bash
cd server
python -m unittest test_app
```

Testler sahte bir Kick API'sine karşı uçtan uca çalışır; gerçek Kick'e istek atmaz. Giriş, yetki
düşüşü, sıra ve eşzamanlı işçiler, ekipler arası adil sıra, ekip silme ve güvenlik kuralları kapsanır.

## Durum ve yol haritası

Çalışan sürüm. Gerçek Kick üzerinde doğrulananlar: giriş, hem yayıncı hem moderatör yetkisiyle ban,
ban kaldırma ve iki kanalda binlerce hesaplık toplu içe aktarma.

- [x] Tokenların veritabanında şifrelenmesi
- [x] Oturumlara süre
- [x] Extension'ın sabit kimliğe bağlanması
- [x] Extension simgesi
- [x] Sunucunun internette HTTPS arkasında, servis olarak çalışması ve veritabanı yedeği
- [x] Ekip silme
- [x] Açık sunucu için sıkılaştırma: ekip oluşturma izni, ekipler arası adil sıra, giriş sınırı
- [ ] Chrome Web Store yayını (inceleme aşamasında)
- [ ] Sohbeti dinleyip spam botlarını şüpheli kuyruğuna alan otomatik yakalama
- [ ] Ekip içinde roller (yalnızca yetkili üyeler ban kaldırabilsin)

## Bilinen sınırlar

- Kullanıcı adı, Kick'in kanal adresi kuralıyla aranır (küçük harf, `_` yerine `-`, en fazla 25 karakter).
- Kanallar ekibe elle eklenir; resmi API "moderatörü olduğum kanallar" listesini vermiyor.
- Süreli banlar süresi dolduktan sonra da listede aktif görünür.
- Hız, Kick'in istek sınırıyla belirlenir: iki kanallı bir ekipte hesap başına yaklaşık bir saniye.

## Lisans

Copyright (C) 2026 Helyosfer

Magnetosphere özgür yazılımdır; [GNU Genel Kamu Lisansı sürüm 3](LICENSE) (GPL-3.0) koşulları altında
kullanabilir, değiştirebilir ve dağıtabilirsin. Değiştirilmiş sürümleri dağıtırsan kaynak kodunu da aynı
lisansla açman gerekir. Yazılım hiçbir garanti verilmeden sunulur.
