# Ev Karnesi

İstanbul'da bir binaya dokun, her kat için bir karne çıksın:

- **Kış güneşi**: 21 Aralık'ta o kata kaç saat doğrudan güneş düşüyor? Komşu binaların ve yamacın gölgesi, her cephe için 15 dakikada bir güneşe doğru ışın gönderilerek hesaplanır.
- **Deniz manzarası**: Pencereden deniz hangi açıyla, hangi yönde görünüyor? Kız Kulesi, köprüler, Tarihi Yarımada görüş hattında mı?
- **Ulaşım ve gündelik ihtiyaç**: Sokak ağı üzerinden raylı sisteme, iskeleye, markete, eczaneye, parka yürüme süresi.
- **Deprem**: İBB'nin Mw 7,5 gece senaryosuna göre mahalle düzeyinde ağır hasar oranı ve bina yaşı dağılımı.

Canlı: https://ulukanyigit.github.io/ev-karnesi/

## Kapsam
İlk aşamada 10 ilçe: Ataşehir, Bakırköy, Beşiktaş, Beyoğlu, Fatih, Kadıköy, Maltepe, Şişli, Ümraniye, Üsküdar (~200 bin bina).

## Veri ve yöntem
| Katman | Kaynak |
|---|---|
| Bina tabanları, kat sayıları, yollar, POI | OpenStreetMap (BBBike İstanbul özeti, 9 Ekim 2026) |
| Arazi / yüzey modeli | Copernicus DEM GLO-30 |
| Bina yüksekliği (model girdisi) | GlobalBuildingAtlas (TUM, CC BY-NC 4.0) |
| Deprem senaryosu, bina yaşı | İBB Açık Veri Portalı |

**Kat sayısı:** OSM'de binaların çoğunda kat bilgisi yok. Kayıtlı ~9.200 binayla eğitilen bir rastgele orman modeli (uydu yüksekliği + taban alanı + bina tipi + çevre dokusu + komşu kayıtlar) eksikleri tahmin eder. İlçe bazında çapraz doğrulama: ±1 kat içinde %58–85. Uygulama her ilçenin doğruluğunu ve her binanın kaynağını (OSM / tahmin / kullanıcı düzeltmesi) gösterir.

**Sınırlar:** Kat yüksekliği 3 m kabul edilir. Uzak (3 km+) deniz manzaraları, ilçe dışındaki binalar uydu yüzey modeliyle temsil edildiği için yaklaşıktır. Deprem bilgisi mahalle düzeyindedir, binaya özel değildir. Bu bir ön inceleme aracıdır, ekspertiz ya da zemin etüdünün yerine geçmez.

## Hat
`pipeline/` klasöründe: `extract_pbf.py` (OSM özetinden ilçe ayıklama) → `height_model2.py` (kat modeli) → `prep2.py` (ilçe verisi) → `precompute2.js` (harita için güneş/manzara) → `build3.py` (site). Hesap motoru `engine.js` hem tarayıcıda hem Node'da çalışır.

## Lisans
Kod: MIT. Veri dosyaları (`data/`) OpenStreetMap türevidir: © OpenStreetMap katkıcıları, ODbL 1.0. GlobalBuildingAtlas türevi alanlar ticari olmayan kullanım içindir (CC BY-NC 4.0).

Hamza Yiğit Ulukan, Harita Mühendisi
