from django.db import migrations


# ── WORDS ─────────────────────────────────────────────────────────────────────
# (word, difficulty, grade_level)
WORDS = [
    # ── EASY / 1. sınıf ──────────────────────────────────────────────────────
    ("EV", "easy", 1), ("SU", "easy", 1), ("EL", "easy", 1), ("GÖZ", "easy", 1),
    ("KUŞ", "easy", 1), ("TOP", "easy", 1), ("BAL", "easy", 1), ("YAY", "easy", 1),
    ("ÇAY", "easy", 1), ("TAŞ", "easy", 1), ("DAĞ", "easy", 1), ("GÜL", "easy", 1),
    ("AT", "easy", 1),  ("OT", "easy", 1),  ("İP", "easy", 1),  ("KAR", "easy", 1),
    ("YER", "easy", 1), ("GÜN", "easy", 1), ("YOL", "easy", 1), ("KOL", "easy", 1),
    ("BUZ", "easy", 1), ("DEĞ", "easy", 1), ("KIZ", "easy", 1), ("BOY", "easy", 1),
    ("SAÇ", "easy", 1), ("DİZ", "easy", 1), ("BEZ", "easy", 1), ("TOZ", "easy", 1),
    ("KAZ", "easy", 1), ("BAŞ", "easy", 1), ("GÖK", "easy", 1), ("NAR", "easy", 1),
    ("CAM", "easy", 1), ("ZİL", "easy", 1), ("FEN", "easy", 1), ("POT", "easy", 1),
    ("RUH", "easy", 1), ("SON", "easy", 1), ("TAM", "easy", 1), ("VAR", "easy", 1),
    # ── EASY / 2. sınıf ──────────────────────────────────────────────────────
    ("KEDI", "easy", 2), ("OKUL", "easy", 2), ("ELMA", "easy", 2), ("MASA", "easy", 2),
    ("BALIK", "easy", 2), ("ARABA", "easy", 2), ("KAPI", "easy", 2), ("ANNE", "easy", 2),
    ("BABA", "easy", 2), ("KALE", "easy", 2), ("KUPA", "easy", 2), ("GECE", "easy", 2),
    ("SABAH", "easy", 2), ("ÇORBA", "easy", 2), ("EKMEK", "easy", 2), ("PEYNIR", "easy", 2),
    ("KÖPEK", "easy", 2), ("ÖRDEK", "easy", 2), ("TAVUK", "easy", 2), ("ASLAN", "easy", 2),
    ("KALEM", "easy", 2), ("DEFTer", "easy", 2), ("SIMIT", "easy", 2), ("BEBEK", "easy", 2),
    ("RENK", "easy", 2), ("YILAN", "easy", 2), ("ÇIÇEK", "easy", 2), ("KİRAZ", "easy", 2),
    ("ÜZÜM", "easy", 2), ("KAVUN", "easy", 2), ("KARPUZ", "easy", 2), ("PORTAKAL", "easy", 2),
    ("MANGO", "easy", 2), ("ARMUT", "easy", 2), ("İNCİR", "easy", 2), ("ŞEFTALI", "easy", 2),
    ("ÇİLEK", "easy", 2), ("AYVA", "easy", 2), ("LIMON", "easy", 2), ("MEYVE", "easy", 2),
    # ── MEDIUM / 2. sınıf ────────────────────────────────────────────────────
    ("KAHRAMAN", "medium", 2), ("OYUNCAK", "medium", 2), ("KİTAPLIK", "medium", 2),
    ("PENCERE", "medium", 2), ("SÖZLÜK", "medium", 2), ("DONDURMA", "medium", 2),
    ("ÇIKOLATA", "medium", 2), ("BISKÜVI", "medium", 2), ("KELEBEK", "medium", 2),
    ("SINCAP", "medium", 2), ("TAVŞAN", "medium", 2), ("FİL", "medium", 2),
    ("MAYMUN", "medium", 2), ("ZÜRAFa", "medium", 2), ("KAPLAN", "medium", 2),
    ("PENGUEN", "medium", 2), ("YUNUS", "medium", 2), ("KARTAL", "medium", 2),
    ("PAPAĞAN", "medium", 2), ("TIMSAH", "medium", 2),
    # ── MEDIUM / 3. sınıf ────────────────────────────────────────────────────
    ("UÇAK", "medium", 3), ("TREN", "medium", 3), ("GEMİ", "medium", 3),
    ("OTOBÜS", "medium", 3), ("MİNİBÜS", "medium", 3), ("BİSİKLET", "medium", 3),
    ("MOTOSİKLET", "medium", 3), ("HELIKOPTER", "medium", 3), ("ROKET", "medium", 3),
    ("DENIZALTI", "medium", 3), ("GÖZLÜK", "medium", 3), ("TELEFON", "medium", 3),
    ("BİLGİSAYAR", "medium", 3), ("KULAKLLIK", "medium", 3), ("TABLET", "medium", 3),
    ("KAMERA", "medium", 3), ("MIKROFON", "medium", 3), ("PIYANO", "medium", 3),
    ("GİTAR", "medium", 3), ("DAVUL", "medium", 3), ("KAVAl", "medium", 3),
    ("KEMAN", "medium", 3), ("SAKSAFON", "medium", 3), ("FLÜT", "medium", 3),
    ("TUĞLA", "medium", 3), ("BETON", "medium", 3), ("MİMAR", "medium", 3),
    ("BAHÇE", "medium", 3), ("HAVUZ", "medium", 3), ("KÖPRÜ", "medium", 3),
    ("KASABA", "medium", 3), ("ŞEHİR", "medium", 3), ("ÜLKE", "medium", 3),
    ("KITA", "medium", 3), ("OKYANUS", "medium", 3), ("DENIZ", "medium", 3),
    ("NEHIR", "medium", 3), ("GÖLET", "medium", 3), ("ÇAĞLAYAN", "medium", 3),
    ("ORMAN", "medium", 3), ("ÇÖLLER", "medium", 3), ("BUZUL", "medium", 3),
    # ── MEDIUM / 4. sınıf ────────────────────────────────────────────────────
    ("ANAYASA", "medium", 4), ("CUMHURIYET", "medium", 4), ("DEMOKRASI", "medium", 4),
    ("ÖZGÜRLÜK", "medium", 4), ("SORUMLULUK", "medium", 4), ("DAYANIŞMA", "medium", 4),
    ("PAYLAŞMAK", "medium", 4), ("YARDIMLAŞMA", "medium", 4), ("DOSTLUK", "medium", 4),
    ("GÜVENİLİRLİK", "medium", 4), ("DÜRÜSTLÜK", "medium", 4), ("SAYGI", "medium", 4),
    ("SEVGİ", "medium", 4), ("HOŞGÖRÜ", "medium", 4), ("BARIŞ", "medium", 4),
    ("ADALET", "medium", 4), ("EŞİTLİK", "medium", 4), ("HAKLILIK", "medium", 4),
    ("ÇALIŞKANLIK", "medium", 4), ("SABIR", "medium", 4),
    # ── HARD / 3. sınıf ──────────────────────────────────────────────────────
    ("ÖĞRETMEN", "hard", 3), ("CUMHURBAŞKANI", "hard", 3), ("PARAKÜTçü", "hard", 3),
    ("ASTRONOT", "hard", 3), ("MÜHENDİS", "hard", 3), ("MİMARLIK", "hard", 3),
    ("DOKTORLUK", "hard", 3), ("HEMŞİRELİK", "hard", 3), ("AVUKaTLIK", "hard", 3),
    ("GAZETECİLİK", "hard", 3), ("FELSEFECİ", "hard", 3), ("TARİHÇİ", "hard", 3),
    ("COĞRAFYACI", "hard", 3), ("PSİKOLOG", "hard", 3), ("SOSYOlOG", "hard", 3),
    ("EKONOMİST", "hard", 3), ("BİYOLOJİST", "hard", 3), ("KİMYAGER", "hard", 3),
    ("FİZİKÇİ", "hard", 3), ("MATEMATİKÇİ", "hard", 3),
    # ── HARD / 4. sınıf ──────────────────────────────────────────────────────
    ("ANAYURDUMUZ", "hard", 4), ("VATANPERVERLIK", "hard", 4), ("MİLLİYETÇİLİK", "hard", 4),
    ("ULUSLARARASI", "hard", 4), ("KÜRESELLEŞME", "hard", 4), ("SÜRDÜRÜLEBILIR", "hard", 4),
    ("ÇEVREKORUMA", "hard", 4), ("YENİLENEBİLİR", "hard", 4), ("EKOSİSTEM", "hard", 4),
    ("BİYOÇEŞİTLİLİK", "hard", 4), ("KARBONAYKIZI", "hard", 4), ("IŞIKIRLAMA", "hard", 4),
    ("GÜNEŞENERJISI", "hard", 4), ("RÜZGARENERJISI", "hard", 4), ("SUENERJİSİ", "hard", 4),
    ("TEKNOLOJIK", "hard", 4), ("YAPAYZEKAS", "hard", 4), ("ROBOTIK", "hard", 4),
    ("NANOTEKNOLOJI", "hard", 4), ("KUANTUMBİLGİSAYAR", "hard", 4),
]

# ── STORIES ────────────────────────────────────────────────────────────────────
# Her hikaye: (title, text, difficulty, grade_level, questions)
# questions: [(question, option_a, option_b, option_c, correct)]  correct = "a"/"b"/"c"

STORIES = [
    # ── EASY / 1. sınıf ──────────────────────────────────────────────────────
    (
        "Minik Kedi",
        "Minik kedi bahçede oynadı. Güneş parlıyordu. Kedi çok mutluydu.",
        "easy", 1,
        [
            ("Kedi nerede oynadı?", "Evde", "Bahçede", "Okulda", "b"),
            ("Hava nasıldı?", "Yağmurluydu", "Karlıydı", "Güneşliydi", "c"),
            ("Kedi nasıl hissediyordu?", "Üzgündü", "Mutluydu", "Korkmuştu", "b"),
        ],
    ),
    (
        "Ali Okula Gitti",
        "Ali sabah okula gitti. Kitabını açtı. Öğretmeni ona baktı ve güldü.",
        "easy", 1,
        [
            ("Ali nereye gitti?", "Eve", "Parka", "Okula", "c"),
            ("Ali ne yaptı?", "Uyudu", "Kitabını açtı", "Koştu", "b"),
            ("Öğretmeni ne yaptı?", "Ağladı", "Güldü", "Kızdı", "b"),
        ],
    ),
    (
        "Yağmur Yağıyor",
        "Bugün yağmur yağıyor. Zeynep şemsiyesini aldı. Islak olmadan okula gitti.",
        "easy", 1,
        [
            ("Bugün hava nasıl?", "Güneşli", "Karlı", "Yağmurlu", "c"),
            ("Zeynep ne aldı?", "Çantasını", "Şemsiyesini", "Kitabını", "b"),
            ("Zeynep nereye gitti?", "Markete", "Parka", "Okula", "c"),
        ],
    ),
    (
        "Küçük Balık",
        "Küçük balık denizde yüzdü. Deniz mavisiydi. Balık arkadaşlarıyla oynadı.",
        "easy", 1,
        [
            ("Balık nerede yüzdü?", "Göldee", "Nehirde", "Denizde", "c"),
            ("Deniz ne renkteydi?", "Kırmızı", "Mavi", "Yeşil", "b"),
            ("Balık ne yaptı?", "Uyudu", "Arkadaşlarıyla oynadı", "Eve gitti", "b"),
        ],
    ),
    (
        "Tohumun Yolculuğu",
        "Bir tohum toprağa düştü. Yağmur yağdı ve ıslandı. Güneş çıkınca küçük bir filiz oluştu.",
        "easy", 1,
        [
            ("Tohum nereye düştü?", "Suya", "Toprağa", "Tasa", "b"),
            ("Tohuma ne oldu önce?", "Yandı", "Yağmurla ıslandı", "Kurudu", "b"),
            ("Sonunda ne oluştu?", "Bir ağaç", "Bir çiçek", "Küçük bir filiz", "c"),
        ],
    ),
    # ── EASY / 2. sınıf ──────────────────────────────────────────────────────
    (
        "Markete Gidiyoruz",
        "Zeynep ve annesi markete gitti. Elma, süt ve ekmek aldılar. Eve dönerken şarkı söylediler.",
        "easy", 2,
        [
            ("Zeynep kiminle markete gitti?", "Babası", "Annesi", "Kardeşi", "b"),
            ("Ne aldılar?", "Ekmek ve su", "Elma, süt ve ekmek", "Çikolata ve meyve", "b"),
            ("Eve dönerken ne yaptılar?", "Koştular", "Şarkı söylediler", "Uyudular", "b"),
        ],
    ),
    (
        "Kar Yağıyor",
        "Bugün kar yağıyor. Sokaklar beyaza büründü. Can ve arkadaşları dışarı çıkıp kartopu oynadı.",
        "easy", 2,
        [
            ("Bugün ne yağıyor?", "Yağmur", "Kar", "Dolu", "b"),
            ("Sokaklar ne renge büründü?", "Sarı", "Mavi", "Beyaz", "c"),
            ("Can ne yaptı?", "Uyudu", "Kartopu oynadı", "Kitap okudu", "b"),
        ],
    ),
    (
        "Rüzgarın Armağanı",
        "Güçlü bir rüzgar esti. Ağaçların yaprakları döküldü. Ayşe sarı yaprakları toplayıp albüme yapıştırdı.",
        "easy", 2,
        [
            ("Ne esti?", "Fırtına", "Güçlü bir rüzgar", "Soğuk hava", "b"),
            ("Ağaçlara ne oldu?", "Devrildi", "Yaprakları döküldü", "Çiçek açtı", "b"),
            ("Ayşe yapraklarla ne yaptı?", "Çöpe attı", "Yaktı", "Albüme yapıştırdı", "c"),
        ],
    ),
    (
        "Balkon Bahçesi",
        "Deniz, balkona çiçek dikti. Her sabah suladı. Bir hafta sonra çiçekler açtı.",
        "easy", 2,
        [
            ("Deniz balkona ne dikti?", "Ağaç", "Çiçek", "Sebze", "b"),
            ("Ne zaman suladı?", "Her akşam", "Her sabah", "Haftada bir", "b"),
            ("Bir hafta sonra ne oldu?", "Çiçekler solar.", "Çiçekler açtı.", "Yapraklar döküldü.", "b"),
        ],
    ),
    (
        "Kütüphanede Bir Gün",
        "Ömer kütüphaneye gitti. Raf raf kitap gezdi. En sonunda bir macera kitabı seçti ve okumaya başladı.",
        "easy", 2,
        [
            ("Ömer nereye gitti?", "Parka", "Kütüphaneye", "Okula", "b"),
            ("Ne yaptı orada?", "Uyudu", "Raf raf kitap gezdi", "Arkadaşlarıyla oynadı", "b"),
            ("Ne tür kitap seçti?", "Masallar", "Ders kitabı", "Macera kitabı", "c"),
        ],
    ),
    # ── MEDIUM / 2. sınıf ────────────────────────────────────────────────────
    (
        "Mert'in Sabahı",
        "Mert sabah erken kalktı. Dişlerini fırçaladı ve kahvaltı yaptı. Ardından çantasını alıp okula koştu. Bugün sınav vardı ama Mert hazırdı.",
        "medium", 2,
        [
            ("Mert ne zaman kalktı?", "Geç saatte", "Sabah erken", "Öğleden sonra", "b"),
            ("Mert kahvaltıdan önce ne yaptı?", "Oyun oynadı", "Dişlerini fırçaladı", "Kitap okudu", "b"),
            ("Mert okula nasıl gitti?", "Yürüdü", "Bisikletle gitti", "Koştu", "c"),
            ("Bugün ne vardı?", "Tatil", "Sınav", "Gezi", "b"),
        ],
    ),
    (
        "Doğum Günü Sürprizi",
        "Bugün Selin'in doğum günüydü. Ailesi küçük bir sürpriz hazırladı. Odaya girince balonlar ve pasta gördü. Selin çok mutlu oldu ve herkesi sarıldı.",
        "medium", 2,
        [
            ("Bugün kimin doğum günü?", "Annenin", "Selin'in", "Arkadaşının", "b"),
            ("Kim sürpriz hazırladı?", "Öğretmeni", "Ailesi", "Komşuları", "b"),
            ("Odada ne gördü?", "Hediyeler ve para", "Balonlar ve pasta", "Çiçekler ve mum", "b"),
            ("Selin ne yaptı?", "Ağladı", "Herkesi sarıldı", "Eve kaçtı", "b"),
        ],
    ),
    (
        "Kayıp Köpek",
        "Küçük köpek Pamuk bahçeden kaçtı. Aile mahallede arama yaptı. Komşular da yardım etti. Akşam üstü Pamuk komşunun bahçesinde bulundu.",
        "medium", 2,
        [
            ("Köpeğin adı neydi?", "Karabaş", "Pamuk", "Boncuk", "b"),
            ("Pamuk nereden kaçtı?", "Evden", "Bahçeden", "Okuldan", "b"),
            ("Kim de yardım etti?", "Öğretmenler", "Komşular", "Polis", "b"),
            ("Pamuk nerede bulundu?", "Parkta", "Markette", "Komşunun bahçesinde", "c"),
        ],
    ),
    (
        "Yıldızları Sayarken",
        "Ece ve dedesi bahçeye çıkıp yıldızları saydı. Dede her yıldızın bir ismi olduğunu anlattı. Ece en parlak yıldıza 'Umut' adını koydu. O gece çok mutlu uyudu.",
        "medium", 2,
        [
            ("Ece kiminle bahçeye çıktı?", "Annesiyle", "Dedesiyle", "Abisiyle", "b"),
            ("Dede ne anlattı?", "Her yıldızın bir ismi olduğunu", "Gökyüzünün mavi olduğunu", "Güneşin büyük olduğunu", "a"),
            ("Ece en parlak yıldıza ne dedi?", "Umut", "Sevinç", "Nur", "a"),
            ("Ece o gece nasıl uyudu?", "Üzgün", "Çok mutlu", "Korkmuş", "b"),
        ],
    ),
    # ── MEDIUM / 3. sınıf ────────────────────────────────────────────────────
    (
        "Okul Gazetesi",
        "3-B sınıfı bir okul gazetesi çıkarmaya karar verdi. Öğrenciler görev aldı: kimisi yazı yazdı, kimisi resim çizdi. Bir hafta uğraşınca gazete hazır oldu. Tüm okul gazeteyi merakla okudu.",
        "medium", 3,
        [
            ("Hangi sınıf gazete çıkardı?", "3-A", "3-B", "4-A", "b"),
            ("Öğrenciler neler yaptı?", "Sadece yazı yazdı", "Yazı yazdı ve resim çizdi", "Sadece resim çizdi", "b"),
            ("Gazete ne kadar sürede hazır oldu?", "Bir gün", "Bir hafta", "Bir ay", "b"),
            ("Gazeteyi kim okudu?", "Yalnızca 3-B", "Tüm okul", "Yalnızca öğretmenler", "b"),
        ],
    ),
    (
        "Küçük Kahraman",
        "Ali parkta oynarken küçük bir kız çocuğunun düştüğünü gördü. Hemen koşup yardım etti. Kızın annesini buldu ve durumu anlattı. Annesi Ali'ye teşekkür etti ve onu 'küçük kahraman' diye övdü.",
        "medium", 3,
        [
            ("Ali nerede oynarken kızı gördü?", "Okulda", "Bahçede", "Parkta", "c"),
            ("Kıza ne olmuştu?", "Düşmüştü", "Kaybolmuştu", "Ağlıyordu", "a"),
            ("Ali ne yaptı?", "Kaçtı", "Koşup yardım etti", "Bağırdı", "b"),
            ("Anne Ali'ye ne dedi?", "Küçük kahraman", "İyi çocuk", "Tatlı şeyler", "a"),
        ],
    ),
    (
        "Doğa Yürüyüşü",
        "Sınıf öğretmenleriyle ormana yürüyüşe çıktı. Meşe palamutu, mantar ve farklı böcekler buldular. Öğretmen her bitkiyi ve böceği anlattı. Öğrenciler not defterlerine çizim yaptı.",
        "medium", 3,
        [
            ("Sınıf nereye gitti?", "Denize", "Ormana", "Şehre", "b"),
            ("Ne buldular?", "Çiçek ve taş", "Meşe palamutu, mantar ve böcekler", "Yılan ve kertenkele", "b"),
            ("Öğretmen ne yaptı?", "Hiçbir şey söylemedi", "Her bitkiyi ve böceği anlattı", "Fotoğraf çekti", "b"),
            ("Öğrenciler ne yaptı?", "Not defterlerine çizim yaptı", "Oyun oynadı", "Eve döndü", "a"),
        ],
    ),
    # ── HARD / 3. sınıf ──────────────────────────────────────────────────────
    (
        "İlk Uzay Yolculuğu",
        "Astronot Tarık, rokete bindi ve uzaya fırlatıldı. Dünya'yı uzaydan ilk kez gördüğünde mavi bir top gibi göründüğünü söyledi. Uçuş boyunca bilimsel deneyler yaptı. Üç gün sonra Dünya'ya döndü ve milyonlarca insana ilham verdi.",
        "hard", 3,
        [
            ("Tarık ne bindi?", "Uçağa", "Rokete", "Helikoptere", "b"),
            ("Dünya uzaydan nasıl göründü?", "Kırmızı bir top gibi", "Mavi bir top gibi", "Yeşil bir top gibi", "b"),
            ("Tarık uzayda ne yaptı?", "Uyudu", "Bilimsel deneyler yaptı", "Fotoğraf çekti", "b"),
            ("Tarık kaç gün sonra döndü?", "Bir", "İki", "Üç", "c"),
            ("Tarık insanlara ne yaptı?", "Korkuttu", "Hayal kırıklığı yarattı", "İlham verdi", "c"),
        ],
    ),
    (
        "Zeytin Hasadı",
        "Her sonbaharda köyde büyük bir zeytin hasadı yapılır. Tüm aile bahçeye iner; çocuklar zeytinleri toplayan ağlara yardım eder. Büyükanne zeytinleri nasıl tuzlayacağını anlatır. Bu gelenek nesilden nesile aktarılmıştır.",
        "hard", 3,
        [
            ("Hasat ne zaman yapılır?", "Her ilkbaharda", "Her sonbaharda", "Her yazın", "b"),
            ("Çocuklar ne yapar?", "Oyun oynar", "Ev temizler", "Ağlara yardım eder", "c"),
            ("Büyükanne ne anlatır?", "Nasıl yemek pişirileceğini", "Zeytinlerin nasıl tuzlanacağını", "Bahçenin nasıl sulanaacağını", "b"),
            ("Bu gelenek nasıl sürer?", "Kitaplarda yazar", "Nesilden nesile aktarılır", "Devlet öğretir", "b"),
        ],
    ),
    # ── HARD / 4. sınıf ──────────────────────────────────────────────────────
    (
        "İklim Değişikliği",
        "İklim değişikliği, Dünya'nın ortalama sıcaklığının artması demektir. Fabrikalar ve araçlar çok fazla karbondioksit salar. Bu gazlar atmosferde birikip ısıyı hapseder. Bilim insanları yenilenebilir enerji kaynaklarına geçilmesi gerektiğini söylüyor.",
        "hard", 4,
        [
            ("İklim değişikliği ne anlama geliyor?", "Havaların soğuması", "Dünyanın ortalama sıcaklığının artması", "Yağışların azalması", "b"),
            ("Karbondioksiti kim salar?", "Ormanlar ve göller", "Fabrikalar ve araçlar", "Okyanus canlıları", "b"),
            ("Gazlar ne yapar?", "Atmosferi temizler", "Isıyı hapseder", "Yağmur oluşturur", "b"),
            ("Bilim insanları ne öneriyor?", "Daha fazla fabrika kurmak", "Yenilenebilir enerjiye geçmek", "Araç kullanımını artırmak", "b"),
        ],
    ),
    (
        "Su Kıtlığı",
        "Dünyanın yüzde yetmişi su ile kaplıdır; fakat bu suyun yüzde ikisi içilebilir niteliktedir. Nüfus artışı ve kirlilik tatlı su kaynaklarını tehdit ediyor. Bilim insanları suyu tasarruflu kullanmayı ve atık suları geri dönüştürmeyi öneriyor. Her birey su tasarrufuna küçük adımlarla katkı sağlayabilir.",
        "hard", 4,
        [
            ("Dünyanın yüzde kaçı suyla kaplı?", "Yüzde elli", "Yüzde yetmiş", "Yüzde doksan", "b"),
            ("İçilebilir su oranı kaç?", "Yüzde on", "Yüzde iki", "Yüzde yirmi", "b"),
            ("Tatlı suları ne tehdit ediyor?", "Yalnızca kirlilik", "Nüfus artışı ve kirlilik", "Yalnızca nüfus artışı", "b"),
            ("Bilim insanları ne öneriyor?", "Daha az su içmek", "Suyu tasarruflu kullanmak ve geri dönüştürmek", "Deniz suyunu kullanmak", "b"),
        ],
    ),
    (
        "Türk Bilim İnsanları",
        "Türkiye, dünyaya pek çok değerli bilim insanı yetiştirmiştir. Aziz Sancar, DNA onarım mekanizmalarını keşfetmesiyle Nobel ödülü almıştır. Cahit Arf, Arf değişmezi adıyla bilinen matematiksel buluşuyla ünlenmiştir. Bu bilim insanları ülkemizin gururu olmaya devam etmektedir.",
        "hard", 4,
        [
            ("Aziz Sancar ne için Nobel ödülü aldı?", "Uzay araştırmaları", "DNA onarım mekanizmalarını keşfetmesi", "Matematik buluşu", "b"),
            ("Cahit Arf neyle ünlüdür?", "Kimya buluşuyla", "Arf değişmezi adlı matematiksel buluşla", "Fizik teorisiyle", "b"),
            ("Bu bilim insanları neyin gururu?", "Ailelerinin", "Ülkemizin", "Dünya tarihinin", "b"),
        ],
    ),
]


def seed_reading_content(apps, schema_editor):
    ReadingWord = apps.get_model("kids", "ReadingWord")
    ReadingStory = apps.get_model("kids", "ReadingStory")
    ReadingStoryQuestion = apps.get_model("kids", "ReadingStoryQuestion")

    # Words
    for word, difficulty, grade_level in WORDS:
        ReadingWord.objects.get_or_create(
            word=word.upper(),
            difficulty=difficulty,
            grade_level=grade_level,
            defaults={"is_active": True},
        )

    # Stories
    for title, text, difficulty, grade_level, questions in STORIES:
        story, created = ReadingStory.objects.get_or_create(
            title=title,
            defaults={
                "text": text,
                "difficulty": difficulty,
                "grade_level": grade_level,
                "is_active": True,
            },
        )
        if created:
            for order, (question, opt_a, opt_b, opt_c, correct) in enumerate(questions):
                ReadingStoryQuestion.objects.create(
                    story=story,
                    question=question,
                    option_a=opt_a,
                    option_b=opt_b,
                    option_c=opt_c,
                    correct=correct,
                    order=order,
                )


class Migration(migrations.Migration):
    dependencies = [
        ("kids", "0064_reading_word_story_models"),
    ]

    operations = [
        migrations.RunPython(seed_reading_content, migrations.RunPython.noop),
    ]
