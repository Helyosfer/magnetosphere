# Chrome Web Store sayfası

Geliştirici panelindeki alanlara yapıştırılacak metinler ve yüklenecek görseller.
Paket: `python tools/paketle.py` → `dist/magnetosphere-<sürüm>.zip`

## Kısa açıklama (manifest `description`, en fazla 132 karakter)

Kick'te moderatörü olduğun tüm kanallarda bir kullanıcıyı tek seferde banla. Ban listeni istersen mod ekibinle paylaş.

## Ayrıntılı açıklama

Mağazadaki açıklama kutusu düz metin kabul eder; aşağıdaki metin olduğu gibi yapıştırılır.

```text
Magnetosphere, birden fazla Kick kanalında moderatörlük yapanlar için bir ban aracıdır. Bir kullanıcıyı bir kez banlarsın; Magnetosphere bu banı listendeki bütün kanallara uygular.

Bir trolü ya da spam botunu her kanalda tek tek banlamakla uğraşmazsın. Kullanıcı adını bir kez yazman yeterli. Kimin kimi, ne zaman ve neden banladığı da kayıt altına alınır.

Magnetosphere'i tek başına kullanabilirsin: kimseyi davet etmeden kanallarını ekler ve ban atarsın. Mod ekibinle kullanırsan herkes aynı ban listesini görür ve bir moderatörün attığı ban, ekibin bütün kanallarına uygulanır.

NELER YAPABİLİRSİN
• Birden çok kanalda tek seferde ban: Kalıcı ban at ya da kullanıcıyı 10 dakika, 1 saat, 1 gün veya 7 gün uzaklaştır.
• Toplu ban: Kullanıcı adlarını yapıştır ya da .txt, .csv veya .json dosyasından yükle (tek seferde 5.000 ada kadar).
• Arka planda işleme: Uzun listeler sunucuda sırayla işlenir. Paneli, hatta tarayıcıyı kapatsan da banlar atılmaya devam eder.
• Ortak ban kaydı: Her banı kimin, ne zaman ve neden attığını, banın hangi kanallarda uygulandığını gör.
• Yeniden deneme: Bir kanalda uygulanamayan banı tek tıkla tekrar dene.
• Geri alma: Bir banı tek tıkla bütün kanallardan kaldır.
• Adıyla ban kaldırma: Kullanıcı adını yaz, banı bütün kanallardan kaldır. Kick'te elle ya da Magnetosphere'den önce atılmış banlar da kaldırılır.
• Sağ tık kısayolu: kick.com'da bir kullanıcı adını seç, sağ tıkla ve "Ekibin tüm kanallarında banla"yı seç.
• Ekip rolleri: Sahip, yönetici, moderatör ve izleyici rolleriyle kimin neyi yapabileceğini belirle.

NASIL BAŞLANIR
1. Uzantıyı ekle ve Kick hesabınla giriş yap.
2. "Tek başıma başla"ya tıkla ya da seni davet eden ekibin kodunu gir.
3. Moderatörü olduğun kanalları ekle. Artık hepsindeki banları tek yerden yönetebilirsin.

GÜVENLİK VE GİZLİLİK
• Şifren sende kalır: Giriş Kick'in kendi sayfasında yapılır; uzantı Kick şifreni görmez.
• Resmi API: Banlar Kick'in resmi API'si üzerinden ve senin moderatör yetkinle atılır. Moderatörü olmadığın bir kanalda banın uygulanması için o kanalın yayıncısının yetkisini ekiple paylaşmış olması gerekir.
• Karar yayıncıda: Yayıncıysan ekibin senin yetkinle ban atıp atamayacağına yalnızca sen karar verirsin. Davetle katıldığın ekiplerde bu paylaşım kapalı başlar.
• Hesap silme: Hesabını istediğin an panelden silebilirsin; oturumların ve Kick'teki erişim izni de silinir.
• Gereksiz erişim yok: Uzantı ziyaret ettiğin sitelere kod eklemez ve gezinme geçmişini okumaz.
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
| Küçük tanıtım kutusu | `tanitim-kucuk-440x280.png` | 440×280 |
| Büyük tanıtım kutusu (isteğe bağlı) | `tanitim-buyuk-1400x560.png` | 1400×560 |

## Paneldeki diğer alanlar

- Web sitesi: https://github.com/Helyosfer/magnetosphere
- Destek URL'si: https://github.com/Helyosfer/magnetosphere/issues
- Gizlilik politikası: https://magnetosphere.helyosfer.me/privacy
