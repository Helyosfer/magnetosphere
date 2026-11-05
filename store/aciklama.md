# Chrome Web Store sayfası

Geliştirici panelindeki alanlara yapıştırılacak metinler ve yüklenecek görseller.
Paket: `python tools/paketle.py` → `dist/magnetosphere-<sürüm>.zip`

## Kısa açıklama (manifest `description`, en fazla 132 karakter)

Kick'te moderatörü olduğun tüm kanallarda bir kullanıcıyı tek seferde banla. Ban listeni istersen mod ekibinle paylaş.

## Ayrıntılı açıklama

Mağazadaki açıklama kutusu düz metin kabul eder; aşağıdaki metin olduğu gibi yapıştırılır.

```text
Magnetosphere, birden fazla Kick kanalında moderatörlük yapanlar için ortak bir ban listesidir.

Bir trolü ya da spam botunu her kanalda ayrı ayrı banlamana gerek yok. Kullanıcı adını bir kez yazman yeterli; Magnetosphere banı listendeki bütün kanallara uygular. Kimin kimi, ne zaman ve neden banladığı da kayda geçer.

Magnetosphere'i tek başına kullanabilir, kimseyi davet etmeden kendi ban listeni kurabilirsin. Ekiple kullandığında herkes aynı listeyi görür ve bir moderatörün attığı ban, ekibin bütün kanallarına uygulanır.

ÖZELLİKLER
• Çoklu kanalda ban: Tek işlemle bütün kanallarda kalıcı ban at ya da kullanıcıyı 10 dakika, 1 saat, 1 gün veya 7 gün uzaklaştır.
• Toplu ban: Kullanıcı adlarını yapıştır ya da .txt, .csv veya .json dosyasından yükle (tek seferde 5.000 ada kadar).
• Arka planda işlem: Uzun listeler sunucuda işlenmeye devam eder; paneli, hatta tarayıcıyı kapatsan bile.
• Liste ve geçmiş: Liste'de kalıcı banları ve süren uzaklaştırmaları, Geçmiş'te kaldırılan banları ve süresi dolan uzaklaştırmaları gör. Her banı kimin, ne zaman ve neden attığı, hangi kanallarda uygulandığı kayıtlıdır.
• Yeniden deneme: Bir kanalda uygulanamayan banı tek tıkla tekrar dene.
• Tüm kanallarda geri alma: Bir banı tek tıkla bütün kanallardan kaldır.
• Adıyla ban kaldırma: Kullanıcı adını yaz, banı bütün kanallardan kaldır. Kick'te elle ya da Magnetosphere'den önce atılmış banlar da kalkar.
• Sağ tıkla banla: kick.com'da sohbette kullanıcının kartını aç, adına sağ tıkla ve "Ekibin tüm kanallarında banla"yı seç. Panel o adla açılır.
• Ekip rolleri: Sahip, yönetici, moderatör ve izleyici rolleriyle kimin neyi yapabileceğini belirle.

NASIL BAŞLANIR?
1. Uzantıyı ekle ve Kick hesabınla giriş yap.
2. "Tek başıma başla"ya tıkla ya da seni davet eden ekibin kodunu gir.
3. Moderatörü olduğun kanalları ekle. Artık hepsindeki banları tek yerden yönetebilirsin.

GÜVENLİK VE GİZLİLİK
• Şifren sende kalır: Giriş Kick'in kendi sayfasında yapılır; uzantı Kick şifreni görmez.
• Resmî API: Banlar Kick'in resmî API'si üzerinden ve senin moderatör yetkinle atılır. Moderatörü olmadığın bir kanalda banın uygulanması için o kanalın yayıncısının yetkisini ekiple paylaşmış olması gerekir.
• Karar yayıncıda: Yayıncıysan ekibin senin yetkinle ban atıp atamayacağına yalnızca sen karar verirsin. Davetle katıldığın ekiplerde bu paylaşım kapalı başlar.
• Gereksiz erişim yok: Uzantı ziyaret ettiğin sitelere kod eklemez ve gezinme geçmişini okumaz.
• Hesap silme: Hesabını ve verilerini istediğin an panelden silebilirsin.
• Açık kaynak: Magnetosphere GPL-3.0 lisansıyla yayımlanır. Kaynak kodu: https://github.com/Helyosfer/magnetosphere

DESTEK VE GERİ BİLDİRİM
Soru, sorun ve önerilerin için: destek@helyosfer.me

Magnetosphere bağımsız bir projedir; Kick ile bağlantılı değildir ve Kick tarafından onaylanmamıştır.
```

## Görseller

| Alan | Dosya | Boyut |
| --- | --- | --- |
| Ekran görüntüsü 1 | `ekran-1-banla.png` | 1280×800 |
| Ekran görüntüsü 2 | `ekran-2-liste.png` | 1280×800 |
| Ekran görüntüsü 3 | `ekran-3-sira.png` | 1280×800 |
| Ekran görüntüsü 4 | `ekran-4-ekip.png` | 1280×800 |
| Ekran görüntüsü 5 | `ekran-5-sagtik.png` | 1280×800 |
| Küçük tanıtım kutusu | `tanitim-kucuk-440x280.png` | 440×280 |
| Büyük tanıtım kutusu (isteğe bağlı) | `tanitim-buyuk-1400x560.png` | 1400×560 |

### Diğer dillerin görselleri (`en/`, `es/`, `pt/`, `ar/`)

Geliştirici panelinde dil seçilip o dilin klasöründeki görseller yüklenir: English → `en/`, Español → `es/`,
Português (Brasil) → `pt/`, العربية → `ar/`. Panel o dilin arayüzüyle, örnek veriyle çekilir; Arapça
görsellerde sahne aynalanır (metin sağda, panel solda).

Yeniden üretmek için: `python tools/magaza_gorselleri.py` (Chromium gerekir). Varsayılan olarak dört dili
birden üretir; tek dil için `python tools/magaza_gorselleri.py es`, Türkçeler için `tr` verilir.

Her klasörde aynı adlı yedi dosya var:

| Alan | Dosya | Boyut |
| --- | --- | --- |
| Ekran görüntüsü 1 | `screenshot-1-ban.png` | 1280×800 |
| Ekran görüntüsü 2 | `screenshot-2-list.png` | 1280×800 |
| Ekran görüntüsü 3 | `screenshot-3-queue.png` | 1280×800 |
| Ekran görüntüsü 4 | `screenshot-4-team.png` | 1280×800 |
| Ekran görüntüsü 5 | `screenshot-5-right-click.png` | 1280×800 |
| Küçük tanıtım kutusu | `promo-small-440x280.png` | 440×280 |
| Büyük tanıtım kutusu (isteğe bağlı) | `promo-marquee-1400x560.png` | 1400×560 |

## Paneldeki diğer alanlar

- Web sitesi: https://github.com/Helyosfer/magnetosphere
- Destek URL'si: https://github.com/Helyosfer/magnetosphere/issues
- Gizlilik politikası: https://magnetosphere.helyosfer.me/privacy
