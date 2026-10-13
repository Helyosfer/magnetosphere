# Chrome Web Store sayfası

Geliştirici panelindeki alanlara yapıştırılacak metinler ve yüklenecek görseller.
Paket: `python tools/paketle.py` → `dist/magnetosphere-<sürüm>.zip`

## Kısa açıklama (manifest `description`, en fazla 132 karakter)

Bir kullanıcıyı moderatörü olduğun tüm Kick kanallarında tek tıkla banla; istersen mod ekibinle ortak ban listesi tut.

## Ayrıntılı açıklama

Magnetosphere, birden fazla Kick kanalında moderatörlük yapanlar için ortak ban listesidir.

Bir trolü ya da spam botunu her kanalda tek tek banlamak zorunda kalmazsın: kullanıcı adını bir kez yazarsın, listendeki tüm kanallarda banlanır ve kimin, kimi, neden banladığı listeye yazılır.

Tek başına kullanabilirsin; kimseyi davet etmen gerekmez. Ekip olarak kullanırsan herkes aynı listeyi görür ve bir kişinin banı bütün kanalları korur.

NELER YAPAR
• Tek işlemle birden çok kanalda kalıcı ban ya da süreli uzaklaştırma (10 dakikadan 7 güne)
• Toplu ban: adları yapıştır ya da .txt, .csv, .json dosyası yükle
• Uzun listeler arka planda işlenir; paneli kapatsan da devam eder
• Ortak liste: kim, ne zaman, neden banladı ve ban hangi kanalda tuttu
• Bir kanalda tutmayan banı tek tıkla yeniden deneme
• Banı tek tıkla tüm kanallarda geri alma
• kick.com'da kullanıcı adını seçip sağ tıkla banlama
• Ekipler için roller: sahip, yönetici, moderatör, izleyici

NASIL BAŞLANIR
1. Uzantıyı kur ve Kick hesabınla giriş yap.
2. "Tek başıma başla"ya bas ya da seni davet eden ekibin kodunu yapıştır.
3. Moderatörü olduğun kanalları ekle; artık hepsinde tek yerden banlayabilirsin.

GÜVENLİK VE GİZLİLİK
• Giriş Kick'in kendi sayfasında yapılır; uzantı Kick şifreni görmez.
• Banlar Kick'in resmi API'si üzerinden, senin moderatör yetkinle atılır. Moderatörü olmadığın kanalda banın tutmaz.
• Yayıncıysan, ekibin senin yetkinle ban atıp atamayacağına yalnızca sen karar verirsin; varsayılan kapalıdır.
• Hesabını ve verilerini istediğin an panelden silebilirsin.
• Uzantı hiçbir siteye içerik betiği eklemez, gezinme geçmişini okumaz.
• Açık kaynaklıdır (GPL-3.0): https://github.com/Helyosfer/magnetosphere

Sorun ya da öneri için: destek@helyosfer.me

Bu uzantı Kick ile bağlantılı ya da Kick tarafından onaylanmış değildir.

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
