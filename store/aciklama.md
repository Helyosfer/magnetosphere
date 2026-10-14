# Chrome Web Store sayfası

Geliştirici panelindeki alanlara yapıştırılacak metinler ve yüklenecek görseller.
Paket: `python tools/paketle.py` → `dist/magnetosphere-<sürüm>.zip`

## Kısa açıklama (manifest `description`, en fazla 132 karakter)

Bir kullanıcıyı moderatörü olduğun tüm Kick kanallarında tek tıkla banla; istersen mod ekibinle ortak ban listesi tut.

## Ayrıntılı açıklama

Mağazadaki açıklama kutusu düz metin kabul eder; aşağıdaki metin olduğu gibi yapıştırılır.

```text
Magnetosphere, birden fazla Kick kanalını yöneten moderatörler için ortak bir ban listesidir.

Bir trolü veya spam botunu her kanalda ayrı ayrı banlamak zorunda değilsin. Kullanıcı adını bir kez girmen yeterli; Magnetosphere, listedeki tüm kanallarda ban işlemini uygular. Ayrıca kimin, kimi, ne zaman ve hangi nedenle banladığı da kaydedilir.

Magnetosphere'i tek başına kullanabilir, kimseyi davet etmeden kendi ban listeni oluşturabilirsin. Bir ekiple kullandığında ise herkes aynı listeye erişir ve bir moderatörün aldığı karar, ekibin yönettiği tüm kanalların korunmasına yardımcı olur.

ÖZELLİKLER
• Çoklu kanal desteği: Tek işlemle birden fazla kanalda kalıcı ban veya 10 dakika ile 7 gün arasında süreli uzaklaştırma uygula.
• Toplu ban: Kullanıcı adlarını doğrudan yapıştır veya .txt, .csv ya da .json dosyası yükle.
• Arka planda işlem: Uzun listeler arka planda işlenmeye devam eder. Paneli kapatsan bile işlem sürer.
• Ortak ban geçmişi: Kimin, kimi, ne zaman ve neden banladığını, işlemin hangi kanalda başarılı olduğunu görüntüle.
• Başarısız işlemleri yeniden deneme: Bir kanalda uygulanamayan banı tek tıkla yeniden dene.
• Her kanalda geri alma: Bir banı tek tıkla tüm kanallarda kaldır.
• Hızlı banlama: kick.com üzerinde bir kullanıcı adını seçip sağ tıklayarak ban işlemini başlat.
• Ekip rolleri: Sahip, yönetici, moderatör ve izleyici rollerini kullanarak ekip erişimini yönet.

NASIL BAŞLANIR?
1. Uzantıyı yükle ve Kick hesabınla giriş yap.
2. "Tek başıma başla" seçeneğine tıkla veya seni davet eden ekibin kodunu gir.
3. Moderatörlük yaptığın kanalları ekle. Artık tüm kanallarındaki ban işlemlerini tek bir yerden yönetebilirsin.

GÜVENLİK VE GİZLİLİK
• Güvenli giriş: Kick hesabına giriş, Kick'in kendi sayfasında yapılır. Uzantı Kick şifreni görmez.
• Resmî API ve yetkilendirme: Ban işlemleri, Kick'in resmî API'si üzerinden ve senin moderatörlük yetkilerin kullanılarak gerçekleştirilir. Moderatörü olmadığın bir kanalda ban işleminin uygulanabilmesi için o kanalın yayıncısının kendi yetkisini ekiple paylaşmış olması gerekir.
• Yetkiler senin kontrolünde: Yayıncıysan, ekibin senin yetkinle ban atıp atamayacağına yalnızca sen karar verirsin. Davetle katıldığın ekiplerde bu özellik varsayılan olarak kapalıdır.
• Verilerini silme: Hesabını ve verilerini istediğin zaman panel üzerinden silebilirsin.
• Gereksiz erişim yok: Uzantı, ziyaret ettiğin sitelere içerik betiği eklemez ve gezinme geçmişini okumaz.
• Açık kaynak: Magnetosphere, GPL-3.0 lisansı altında yayımlanır. Kaynak koduna GitHub üzerinden ulaşabilirsin: https://github.com/Helyosfer/magnetosphere

DESTEK VE GERİ BİLDİRİM
Soruların, sorunların veya önerilerin için: destek@helyosfer.me

Magnetosphere, Kick ile bağlantılı değildir ve Kick tarafından onaylanmamıştır.
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
