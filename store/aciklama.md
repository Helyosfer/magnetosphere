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
• Toplu ban: Kullanıcı adlarını yapıştır ya da .txt, .csv veya .json dosyasından yükle (tek seferde 6.000 ada kadar).
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
• Karar yayıncıda: Yayıncıysan ekibin senin yetkinle ban atıp atamayacağına yalnızca sen karar verirsin. Bu paylaşım herkes için kapalı başlar.
• Verilerin şifreli: Kick erişim anahtarların ve ekip davet kodları sunucuda şifreli saklanır; uzantıyla sunucu arasındaki bağlantı her zaman şifrelidir (HTTPS).
• Yapay zekâ destekli güvenlik: Sunucu altyapısı, veritabanı ve kod, siber güvenlik odaklı yapay zekâ modelleri desteğiyle denetlenir ve güncellenir; bulunan açıklar yeni sürümlerde kapatılır.
• Gereksiz erişim yok: Uzantı ziyaret ettiğin sitelere kod eklemez ve gezinme geçmişini okumaz.
• Hesap silme: Hesabını ve verilerini istediğin an panelden silebilirsin.
• Açık kaynak: Magnetosphere GPL-3.0 lisansıyla yayımlanır. Kaynak kodu: https://github.com/Helyosfer/magnetosphere

DESTEK VE GERİ BİLDİRİM
Soru, sorun ve önerilerin için: destek@helyosfer.me

Magnetosphere bağımsız bir projedir; Kick ile bağlantılı değildir ve Kick tarafından onaylanmamıştır.
```

## Güvenlik bölümü, diğer diller

Geliştirici panelinde her dilin ayrıntılı açıklamasındaki güvenlik bölümü aşağıdakiyle değiştirilir. Metinler
Türkçedekiyle aynı iddiaları taşır; birinde değişiklik yapılırsa hepsi birlikte güncellenmeli. Model ya da
erişim programı adı bilerek geçmez.

### English

```text
SECURITY AND PRIVACY
• Your password stays with you: You sign in on Kick's own page; the extension never sees your Kick password.
• Official API: Bans are placed through Kick's official API, with your own moderator permissions. For a ban to apply on a channel where you're not a moderator, that channel's streamer must have shared their permission with the team.
• The streamer decides: If you're a streamer, only you decide whether the team can ban with your permission. This sharing is off for everyone by default.
• Your data is encrypted: Your Kick access tokens and team invite codes are stored encrypted on the server, and the connection between the extension and the server is always encrypted (HTTPS).
• AI-assisted security: The server infrastructure, database and code are audited and updated with the help of cybersecurity-focused AI models; vulnerabilities that are found are fixed in new releases.
• No unnecessary access: The extension doesn't inject code into the sites you visit and doesn't read your browsing history.
• Account deletion: You can delete your account and data from the panel at any time.
• Open source: Magnetosphere is released under the GPL-3.0 license. Source code: https://github.com/Helyosfer/magnetosphere
```

### Español

```text
SEGURIDAD Y PRIVACIDAD
• Tu contraseña es solo tuya: Inicias sesión en la propia página de Kick; la extensión nunca ve tu contraseña de Kick.
• API oficial: Los baneos se aplican a través de la API oficial de Kick y con tus propios permisos de moderador. Para que un baneo se aplique en un canal donde no eres moderador, el streamer de ese canal debe haber compartido su permiso con el equipo.
• Decide el streamer: Si eres streamer, solo tú decides si el equipo puede banear con tu permiso. Esta opción viene desactivada para todos.
• Tus datos, cifrados: Tus tokens de acceso de Kick y los códigos de invitación del equipo se guardan cifrados en el servidor, y la conexión entre la extensión y el servidor siempre está cifrada (HTTPS).
• Seguridad con apoyo de IA: La infraestructura del servidor, la base de datos y el código se auditan y actualizan con el apoyo de modelos de IA especializados en ciberseguridad; las vulnerabilidades encontradas se corrigen en nuevas versiones.
• Sin accesos innecesarios: La extensión no inserta código en los sitios que visitas ni lee tu historial de navegación.
• Eliminación de la cuenta: Puedes eliminar tu cuenta y tus datos desde el panel cuando quieras.
• Código abierto: Magnetosphere se publica bajo la licencia GPL-3.0. Código fuente: https://github.com/Helyosfer/magnetosphere
```

### Português (Brasil)

```text
SEGURANÇA E PRIVACIDADE
• Sua senha fica com você: O login é feito na própria página da Kick; a extensão nunca vê sua senha da Kick.
• API oficial: Os bans são aplicados pela API oficial da Kick, com as suas próprias permissões de moderador. Para que um ban valha em um canal onde você não é moderador, o streamer desse canal precisa ter compartilhado a permissão dele com a equipe.
• Quem decide é o streamer: Se você é streamer, só você decide se a equipe pode banir com a sua permissão. Esse compartilhamento vem desativado para todos.
• Seus dados criptografados: Seus tokens de acesso da Kick e os códigos de convite da equipe ficam criptografados no servidor, e a conexão entre a extensão e o servidor é sempre criptografada (HTTPS).
• Segurança com apoio de IA: A infraestrutura do servidor, o banco de dados e o código são auditados e atualizados com o apoio de modelos de IA focados em cibersegurança; as vulnerabilidades encontradas são corrigidas em novas versões.
• Sem acessos desnecessários: A extensão não insere código nos sites que você visita e não lê seu histórico de navegação.
• Exclusão da conta: Você pode excluir sua conta e seus dados pelo painel quando quiser.
• Código aberto: O Magnetosphere é publicado sob a licença GPL-3.0. Código-fonte: https://github.com/Helyosfer/magnetosphere
```

### العربية

```text
الأمان والخصوصية
• كلمة مرورك تبقى لك: يتم تسجيل الدخول في صفحة Kick نفسها، ولا ترى الإضافة كلمة مرور Kick الخاصة بك أبدًا.
• واجهة برمجية رسمية: يُطبَّق الحظر عبر واجهة Kick البرمجية الرسمية وبصلاحيات الإشراف الخاصة بك. ولكي يُطبَّق الحظر في قناة لست مشرفًا فيها، يجب أن يكون صاحب تلك القناة قد شارك صلاحيته مع الفريق.
• القرار لصاحب القناة: إذا كنت صاحب قناة، فأنت وحدك من يقرر ما إذا كان الفريق يستطيع الحظر بصلاحيتك. هذه المشاركة معطّلة افتراضيًا للجميع.
• بياناتك مشفّرة: تُخزَّن رموز الوصول إلى Kick ورموز دعوة الفريق مشفّرةً على الخادم، والاتصال بين الإضافة والخادم مشفّر دائمًا (HTTPS).
• أمان بمساعدة الذكاء الاصطناعي: تُدقَّق البنية التحتية للخادم وقاعدة البيانات والشيفرة وتُحدَّث بمساعدة نماذج ذكاء اصطناعي متخصصة في الأمن السيبراني، وتُصلَح الثغرات المكتشفة في الإصدارات الجديدة.
• لا وصول غير ضروري: لا تضيف الإضافة شيفرة إلى المواقع التي تزورها ولا تقرأ سجل التصفح.
• حذف الحساب: يمكنك حذف حسابك وبياناتك من اللوحة في أي وقت.
• مفتوح المصدر: يُنشر Magnetosphere بترخيص GPL-3.0. الشيفرة المصدرية: https://github.com/Helyosfer/magnetosphere
```

### Deutsch

```text
SICHERHEIT UND DATENSCHUTZ
• Dein Passwort bleibt bei dir: Die Anmeldung erfolgt auf Kicks eigener Seite; die Erweiterung sieht dein Kick-Passwort nie.
• Offizielle API: Banns werden über Kicks offizielle API und mit deinen eigenen Moderatorrechten vergeben. Damit ein Bann in einem Kanal greift, in dem du kein Moderator bist, muss der Streamer dieses Kanals seine Berechtigung mit dem Team geteilt haben.
• Der Streamer entscheidet: Wenn du Streamer bist, entscheidest nur du, ob das Team mit deiner Berechtigung bannen darf. Diese Freigabe ist für alle standardmäßig aus.
• Deine Daten sind verschlüsselt: Deine Kick-Zugriffstoken und die Einladungscodes des Teams werden verschlüsselt auf dem Server gespeichert, und die Verbindung zwischen Erweiterung und Server ist immer verschlüsselt (HTTPS).
• KI-gestützte Sicherheit: Serverinfrastruktur, Datenbank und Code werden mit Unterstützung von auf Cybersicherheit spezialisierten KI-Modellen geprüft und aktualisiert; gefundene Schwachstellen werden in neuen Versionen behoben.
• Kein unnötiger Zugriff: Die Erweiterung fügt keinen Code in besuchte Websites ein und liest deinen Browserverlauf nicht.
• Konto löschen: Du kannst dein Konto und deine Daten jederzeit im Panel löschen.
• Open Source: Magnetosphere steht unter der GPL-3.0-Lizenz. Quellcode: https://github.com/Helyosfer/magnetosphere
```

### Français

```text
SÉCURITÉ ET CONFIDENTIALITÉ
• Ton mot de passe reste à toi : la connexion se fait sur la page de Kick elle-même ; l'extension ne voit jamais ton mot de passe Kick.
• API officielle : les bans passent par l'API officielle de Kick, avec tes propres droits de modérateur. Pour qu'un ban s'applique sur une chaîne où tu n'es pas modérateur, le streamer de cette chaîne doit avoir partagé son autorisation avec l'équipe.
• Le streamer décide : si tu es streamer, toi seul décides si l'équipe peut bannir avec ton autorisation. Ce partage est désactivé par défaut pour tout le monde.
• Tes données sont chiffrées : tes jetons d'accès Kick et les codes d'invitation de l'équipe sont stockés chiffrés sur le serveur, et la connexion entre l'extension et le serveur est toujours chiffrée (HTTPS).
• Sécurité assistée par IA : l'infrastructure du serveur, la base de données et le code sont audités et mis à jour avec l'aide de modèles d'IA spécialisés en cybersécurité ; les failles trouvées sont corrigées dans les nouvelles versions.
• Aucun accès superflu : l'extension n'injecte pas de code dans les sites que tu visites et ne lit pas ton historique de navigation.
• Suppression du compte : tu peux supprimer ton compte et tes données depuis le panneau à tout moment.
• Open source : Magnetosphere est publié sous licence GPL-3.0. Code source : https://github.com/Helyosfer/magnetosphere
```

### Русский

```text
БЕЗОПАСНОСТЬ И КОНФИДЕНЦИАЛЬНОСТЬ
• Пароль остаётся у тебя: вход выполняется на странице самого Kick; расширение никогда не видит твой пароль от Kick.
• Официальный API: баны выдаются через официальный API Kick и с твоими собственными правами модератора. Чтобы бан сработал на канале, где ты не модератор, стример этого канала должен открыть команде доступ к своим правам.
• Решает стример: если ты стример, только ты решаешь, может ли команда банить с твоими правами. По умолчанию этот доступ выключен у всех.
• Данные зашифрованы: твои токены доступа Kick и коды приглашения команды хранятся на сервере в зашифрованном виде, а соединение между расширением и сервером всегда зашифровано (HTTPS).
• Безопасность с помощью ИИ: серверная инфраструктура, база данных и код проверяются и обновляются с помощью ИИ-моделей, специализирующихся на кибербезопасности; найденные уязвимости исправляются в новых версиях.
• Никакого лишнего доступа: расширение не внедряет код на посещаемые сайты и не читает историю браузера.
• Удаление аккаунта: ты можешь в любой момент удалить свой аккаунт и данные из панели.
• Открытый исходный код: Magnetosphere распространяется по лицензии GPL-3.0. Исходный код: https://github.com/Helyosfer/magnetosphere
```

### Bahasa Indonesia

```text
KEAMANAN DAN PRIVASI
• Kata sandimu tetap milikmu: Login dilakukan di halaman Kick sendiri; ekstensi tidak pernah melihat kata sandi Kick-mu.
• API resmi: Ban diberikan lewat API resmi Kick dengan izin moderatormu sendiri. Agar ban berlaku di channel tempat kamu bukan moderator, streamer channel itu harus sudah membagikan izinnya ke tim.
• Streamer yang memutuskan: Kalau kamu streamer, hanya kamu yang memutuskan apakah tim boleh memberi ban dengan izinmu. Berbagi izin ini nonaktif untuk semua orang secara bawaan.
• Datamu terenkripsi: Token akses Kick-mu dan kode undangan tim disimpan terenkripsi di server, dan koneksi antara ekstensi dan server selalu terenkripsi (HTTPS).
• Keamanan berbantuan AI: Infrastruktur server, database, dan kode diaudit dan diperbarui dengan bantuan model AI yang berfokus pada keamanan siber; celah yang ditemukan diperbaiki di versi baru.
• Tanpa akses berlebih: Ekstensi tidak menyisipkan kode ke situs yang kamu kunjungi dan tidak membaca riwayat penjelajahanmu.
• Hapus akun: Kamu bisa menghapus akun dan datamu dari panel kapan saja.
• Sumber terbuka: Magnetosphere dirilis dengan lisensi GPL-3.0. Kode sumber: https://github.com/Helyosfer/magnetosphere
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
