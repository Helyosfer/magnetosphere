# Güvenlik Politikası

[English version below](#security-policy-english)

Magnetosphere, Kick moderatörlerinin OAuth tokenlarını ve ekiplerin ban listelerini işler. Bu yüzden
güvenlik açıklarını ciddiye alıyoruz ve bunları sorumlu biçimde bildiren araştırmacılara teşekkür ederiz.

## Desteklenen sürümler

Güvenlik düzeltmeleri yalnızca en son sürüme yapılır.

| Bileşen | Desteklenen | Desteklenmeyen |
|---|---|---|
| Tarayıcı uzantısı (`extension/`) | Chrome Web Store'daki en son sürüm (şu an 0.15.x) | Daha eski sürümler |
| Sunucu (`server/`) | `main` dalının son hâli | Eski commitler ve değiştirilmiş kopyalar |
| Resmî sunucu | `https://magnetosphere.helyosfer.me` | — |

## Açık nasıl bildirilir

**Lütfen güvenlik açıkları için herkese açık bir GitHub issue, pull request ya da tartışma açma.**

Bildirimini **`destek@helyosfer.me`** adresine gönder. Konu satırına `[GÜVENLİK]` yazman iletinin
hızlı ayrılmasını sağlar. Bildirimde mümkünse şunlar olsun:

- Etkilenen bileşen ve sürüm (uzantı sürümü, sunucu commit'i ya da resmî sunucu).
- Açığın türü (ör. yetki atlatma, ekipler arası veri sızıntısı, XSS, token sızıntısı, OAuth akışı hatası).
- Yeniden üretme adımları ya da kavram kanıtı (PoC). Mümkünse kendi yerel sunucunda üretilmiş olsun.
- Etkisi: saldırgan ne elde ediyor, hangi ön koşullar gerekiyor.
- Varsa önerdiğin düzeltme.
- İsmini teşekkür listesinde görmek isteyip istemediğin ve nasıl anılmak istediğin.

Bildirim Türkçe ya da İngilizce olabilir.

## Ne zaman yanıt alırsın

Magnetosphere gönüllü olarak geliştirilen küçük bir projedir; yine de şu sürelere uymaya çalışırız:

| Aşama | Hedef süre |
|---|---|
| Bildirimin alındığının onayı | 3 iş günü |
| İlk değerlendirme ve önem derecesi | 7 iş günü |
| Kritik ve yüksek önemdeki açıklar için düzeltme | 30 gün |
| Orta ve düşük önemdeki açıklar için düzeltme | 90 gün |

Süreç boyunca seni bilgilendiririz. Bir düzeltme gecikecekse nedenini söyleriz.

## Kapsam

**Kapsam içi:**

- `server/`: Python sunucusu (API, OAuth/PKCE akışı, oturum yönetimi, roller, ekip yalıtımı, sıra işleme).
- `server/web/`: davet sayfası.
- `extension/`: Chrome uzantısı (panel, service worker, sağ tık menüsü, sunucu adresi denetimi).
- `tools/sifreleme_dogrula.py`: şifreleme doğrulama aracı.
- `https://magnetosphere.helyosfer.me` resmî sunucusu: aşağıdaki test kurallarına uyulması şartıyla.

Özellikle ilgilendiğimiz konular:

- Bir ekibin kanallarına, üyelerine ya da ban listesine üyesi olmayan birinin erişebilmesi.
- Rol denetiminin atlatılması (ör. moderatörün yönetici ya da sahip işlemi yapabilmesi).
- Kick access/refresh tokenlarının ya da oturum anahtarlarının sızması veya düz metin saklanması.
- OAuth akışında `state`/PKCE atlatma, açık yönlendirme, oturumun yanlış hedefe teslimi.
- Yayıncı yetkisinin, yayıncı paylaşımı açmadan kullanılabilmesi.
- Panelde ya da davet sayfasında XSS.
- İzinli olmayan bir uzantının API'yi çağırabilmesi (CORS / `ALLOWED_EXTENSION_IDS` atlatma).

**Kapsam dışı:**

- Kick'in kendi platformundaki ya da API'sindeki açıklar (bunları doğrudan Kick'e bildir).
- Kendi kurduğun ve yanlış yapılandırdığın sunucular (ör. `TOKEN_ENCRYPTION_KEY` tanımlanmamış ya da
  HTTPS olmadan açılmış sunucu). README'deki "Bilinen sınırlar" bölümünde zaten belirtilen konular.
- Hizmet engelleme (DoS/DDoS), yük ve hız sınırı testleri.
- Sosyal mühendislik, kimlik avı ve fiziksel saldırılar.
- Kullanıcının tarayıcısının ya da bilgisayarının önceden ele geçirilmiş olmasını gerektiren senaryolar.
- Güvenlik etkisi gösterilmemiş otomatik tarayıcı çıktıları, eksik "en iyi uygulama" başlıkları ve
  sürüm bilgisi ifşası.
- Üçüncü taraf bağımlılıklardaki, bu projede istismar edilebilirliği gösterilmemiş açıklar.

## Test kuralları

Resmî sunucuda test yapacaksan:

- Yalnızca **kendi oluşturduğun hesaplar, ekipler ve kanallar** üzerinde çalış. Başka kullanıcıların
  verisine erişirsen hemen dur, veriyi saklama ve durumu bildirimine yaz.
- Gerçek kanallarda ban atan ya da kaldıran testler yapma; mümkünse kendi yerel sunucunu kur
  (README'deki "Kendi sunucunu kurmak" bölümü).
- Hizmeti yavaşlatacak ya da kesecek testler, otomatik yüksek hacimli tarama ve kaba kuvvet denemeleri yapma.
- Açığı, düzeltme yayımlanana ve biz kabul edene kadar başkalarıyla paylaşma.

## Koordineli açıklama

- Bildirimi aldıktan sonra açığı doğrular, düzeltir ve yeni sürümü yayımlarız.
- Düzeltme yayımlandıktan sonra, seninle birlikte belirlenen bir tarihte açığı kamuya açıklarız
  (gerekirse GitHub Security Advisory ve CVE ile). Varsayılan azami süre bildirimden itibaren 90 gündür.
- İstersen bildirimde ve sürüm notlarında adınla anılırsın.

## Güvenli liman

Bu politikaya iyi niyetle uyan güvenlik araştırmalarını yetkili sayarız ve bu araştırmalar nedeniyle
hukuki işlem başlatmayız. Bir üçüncü taraf seni bu politikaya uygun araştırman yüzünden hedef alırsa,
araştırmanın bu politika çerçevesinde yapıldığını açıkça beyan ederiz. Bir işlemin kapsam içinde olup
olmadığından emin değilsen önce bize sor.

Magnetosphere şu anda para ödüllü bir hata ödül programı yürütmüyor.

## Mevcut güvenlik önlemleri

Hangi önlemlerin alındığı, bilinen sınırlar ve Ekim 2026'daki bağımsız denetimin sonuçları
[README'nin Güvenlik bölümünde](README.md#güvenlik) anlatılır.

---

# Security Policy (English)

Magnetosphere handles Kick moderators' OAuth tokens and teams' ban lists. We take security issues
seriously and thank researchers who report them responsibly.

## Supported versions

Security fixes are released only for the latest version.

| Component | Supported | Not supported |
|---|---|---|
| Browser extension (`extension/`) | Latest version on the Chrome Web Store (currently 0.15.x) | Older versions |
| Server (`server/`) | Latest `main` branch | Older commits and modified forks |
| Official server | `https://magnetosphere.helyosfer.me` | — |

## Reporting a vulnerability

**Please do not open public GitHub issues, pull requests or discussions for security vulnerabilities.**

Send your report to **`destek@helyosfer.me`**, ideally with `[SECURITY]` in the subject line. Please include:

- Affected component and version (extension version, server commit, or the official server).
- Vulnerability type (e.g. authorization bypass, cross-team data leak, XSS, token leak, OAuth flow flaw).
- Steps to reproduce or a proof of concept, preferably reproduced against your own local server.
- Impact: what an attacker gains and which preconditions are required.
- A suggested fix, if you have one.
- Whether and how you would like to be credited.

Reports may be written in English or Turkish.

## Response times

Magnetosphere is a small, volunteer-maintained project. We aim for:

| Stage | Target |
|---|---|
| Acknowledgement of receipt | 3 business days |
| Initial assessment and severity | 7 business days |
| Fix for critical and high severity issues | 30 days |
| Fix for medium and low severity issues | 90 days |

We will keep you informed throughout and explain any delay.

## Scope

**In scope:**

- `server/`: Python server (API, OAuth/PKCE flow, session handling, roles, team isolation, queue processing).
- `server/web/`: invite page.
- `extension/`: Chrome extension (panel, service worker, context menu, server URL checks).
- `tools/sifreleme_dogrula.py`: encryption verification tool.
- The official server at `https://magnetosphere.helyosfer.me`, subject to the testing rules below.

Areas of particular interest:

- Access to a team's channels, members or ban list by a non-member.
- Role check bypass (e.g. a moderator performing admin or owner actions).
- Leakage or plaintext storage of Kick access/refresh tokens or session keys.
- `state`/PKCE bypass, open redirects, or session delivery to the wrong target in the OAuth flow.
- Use of a broadcaster's ban permission without the broadcaster enabling sharing.
- XSS in the panel or invite page.
- An unauthorized extension being able to call the API (CORS / `ALLOWED_EXTENSION_IDS` bypass).

**Out of scope:**

- Vulnerabilities in Kick's own platform or API (report those to Kick directly).
- Self-hosted servers that are misconfigured (e.g. no `TOKEN_ENCRYPTION_KEY`, exposed without HTTPS),
  and issues already listed under "Bilinen sınırlar" (Known limitations) in the README.
- Denial of service (DoS/DDoS), load and rate-limit testing.
- Social engineering, phishing and physical attacks.
- Scenarios that require an already compromised browser or device.
- Automated scanner output, missing "best practice" headers or version disclosure without demonstrated impact.
- Vulnerabilities in third-party dependencies without a demonstrated exploit in this project.

## Testing rules

When testing against the official server:

- Only use **accounts, teams and channels you created yourself**. If you access other users' data,
  stop immediately, do not retain it, and mention it in your report.
- Do not run tests that ban or unban users on real channels; prefer a local server
  (see "Kendi sunucunu kurmak" in the README).
- No testing that degrades or interrupts the service, no high-volume automated scanning, no brute force.
- Do not share the vulnerability with others until a fix is released and we agree to disclosure.

## Coordinated disclosure

- We verify, fix and release a new version after receiving your report.
- After the fix is released, we publish the issue on a date agreed with you (via a GitHub Security
  Advisory and CVE where appropriate). The default maximum is 90 days from the report.
- With your permission, we credit you in the advisory and release notes.

## Safe harbor

We consider security research conducted in good faith and in line with this policy to be authorized,
and we will not pursue legal action over it. If a third party takes action against you for research
that followed this policy, we will make clear that your research was conducted under it. If you are
unsure whether something is in scope, ask us first.

Magnetosphere does not currently run a paid bug bounty program.

## Existing security measures

The protections in place, known limitations and the results of the independent October 2026 audit are
described in the [Security section of the README](README.md#güvenlik) (in Turkish).
