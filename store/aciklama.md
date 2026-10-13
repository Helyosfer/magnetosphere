# Chrome Web Store sayfası

Geliştirici panelindeki alanlara yapıştırılacak metinler ve yüklenecek görseller.
Paket: `python tools/paketle.py` → `dist/magnetosphere-<sürüm>.zip`

## Kısa açıklama (manifest `description`, en fazla 132 karakter)

Mod ekibinle ortak ban listesi tut; bir kullanıcıyı ekibin tüm Kick kanallarında tek tıkla banla.

## Ayrıntılı açıklama

Magnetosphere, Kick moderasyon ekipleri için ortak ban listesidir.

Birden fazla kanalda moderatörlük yapan ekipler, bir trolü ya da spam botunu her kanalda tek tek banlamak zorunda kalır. Magnetosphere bunu tek işleme indirir: kullanıcı adını bir kez yazarsın, ekibin tüm kanallarında banlanır ve kimin, kimi, neden banladığı ortak listeye yazılır.

NELER YAPAR
• Tek işlemle birden çok kanalda kalıcı ban ya da süreli uzaklaştırma (10 dakikadan 7 güne)
• Toplu ban: adları yapıştır ya da .txt, .csv, .json dosyası yükle
• Uzun listeler arka planda işlenir; paneli kapatsan da devam eder
• Ortak liste: kim, ne zaman, neden banladı ve ban hangi kanalda tuttu
• Bir kanalda tutmayan banı tek tıkla yeniden deneme
• Banı tek tıkla tüm kanallarda geri alma
• kick.com'da kullanıcı adını seçip sağ tıkla banlama

NASIL BAŞLANIR
1. Uzantıyı kur ve Kick hesabınla giriş yap.
2. Ekip kur ya da ekibinden aldığın davet koduyla katıl.
3. Ekibi kuran kişi kanalları ekler; artık herkes tek yerden banlayabilir.

GÜVENLİK VE GİZLİLİK
• Giriş Kick'in kendi sayfasında yapılır; uzantı Kick şifreni görmez.
• Banlar Kick'in resmi API'si üzerinden, senin moderatör yetkinle atılır.
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
