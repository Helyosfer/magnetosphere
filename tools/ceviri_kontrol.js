// Çevirilerin eksiksizliğini denetler: node tools/ceviri_kontrol.js
// - Her dil, İngilizcedeki bütün metin anahtarlarına sahip ve fazlası yok.
// - Metin fonksiyonları örnek girdilerle hata vermeden metin döndürüyor.
// - Her dilin _locales klasörü var; mağaza kısa açıklaması 132 karakteri geçmiyor.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const EXT = path.join(__dirname, "..", "extension");
const context = { chrome: { i18n: { getUILanguage: () => "en" } }, Intl };
vm.createContext(context);
vm.runInContext(`${fs.readFileSync(path.join(EXT, "i18n.js"), "utf8")}
  globalThis.STRINGS = STRINGS; globalThis.LANGS = LANGS;`, context);
const { STRINGS, LANGS } = context;

// Chrome'un _locales klasör adı; Brezilya Portekizcesi "pt_BR" olarak aranır.
const LOCALE_DIR = { pt: "pt_BR" };
const SAMPLE_ROLE = { tr: "Moderatör", en: "Moderator", es: "Moderador", pt: "Moderador", ar: "مشرف" };
const problems = [];
const base = Object.keys(STRINGS.en);

for (const lang of LANGS) {
  const table = STRINGS[lang];
  if (!table) {
    problems.push(`${lang}: STRINGS içinde tablo yok`);
    continue;
  }
  const keys = Object.keys(table);
  for (const key of base.filter((k) => !keys.includes(k))) problems.push(`${lang}: eksik anahtar "${key}"`);
  for (const key of keys.filter((k) => !base.includes(k))) problems.push(`${lang}: fazla anahtar "${key}"`);

  for (const [key, value] of Object.entries(table)) {
    if (typeof value !== "function") continue;
    // Sayılar için hem 1 hem 2 hem 11 denenir (tekil, ikili ve çoğul biçimler).
    for (const n of [1, 2, 11]) {
      const args = [n, n + 1, "örnek"].slice(0, value.length);
      if (key === "roleChanged") args[1] = SAMPLE_ROLE[lang];
      let out;
      try {
        out = value(...args);
      } catch (e) {
        problems.push(`${lang}.${key}(${args.join(", ")}): ${e.message}`);
        continue;
      }
      if (typeof out !== "string" || out.includes("undefined")) problems.push(`${lang}.${key}(${args.join(", ")}): "${out}"`);
    }
  }

  const file = path.join(EXT, "_locales", LOCALE_DIR[lang] || lang, "messages.json");
  if (!fs.existsSync(file)) {
    problems.push(`${lang}: ${path.relative(EXT, file)} yok`);
    continue;
  }
  const description = JSON.parse(fs.readFileSync(file, "utf8")).description?.message || "";
  if (!description) problems.push(`${lang}: mağaza kısa açıklaması boş`);
  if (description.length > 132) problems.push(`${lang}: mağaza kısa açıklaması ${description.length} karakter (en fazla 132)`);
}

if (problems.length) {
  console.error(`${problems.length} sorun:\n${problems.map((p) => `  - ${p}`).join("\n")}`);
  process.exit(1);
}
console.log(`Çeviriler tamam: ${LANGS.length} dil, ${base.length} metin.`);
