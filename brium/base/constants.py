from __future__ import annotations

TURKISH_NEWS_SITES: list[str] = [
    "https://www.sozcu.com.tr",
    "https://www.hurriyet.com.tr",
    "https://www.haberturk.com",
    "https://www.ntv.com.tr",
    "https://t24.com.tr",
    "https://www.cumhuriyet.com.tr",
    "https://trthaber.com",
    "https://www.milliyet.com.tr",
    "https://www.ensonhaber.com",
    "https://www.mynet.com",
    "https://www.ahaber.com.tr",
    "https://www.yenisafak.com",
]

NEWS_RSS: list[str] = [
    "https://www.sozcu.com.tr/rss/gundem.xml",
    "https://www.hurriyet.com.tr/rss/anasayfa",
    "https://www.haberturk.com/rss",
    "https://www.bbc.com/turkce/index.xml",
    "https://www.yenisafak.com/rss?cat=1",
]

DEFAULT_HOMEPAGES: list[str] = [
    "https://en.wikipedia.org",
    "https://tr.wikipedia.org",
    "https://www.bbc.com/news",
    "https://www.aljazeera.com",
    *TURKISH_NEWS_SITES,
]

NEWS_DOMAINS: set[str] = {
    "ntv.com.tr", "hurriyet.com.tr", "sozcu.com.tr", "cumhuriyet.com.tr",
    "milliyet.com.tr", "haberturk.com", "t24.com.tr", "dw.com",
    "bbc.com", "bbc.co.uk", "aljazeera.com", "reuters.com",
    "apnews.com", "cnn.com", "cnnturk.com", "trthaber.com",
    "aa.com.tr", "dunya.com", "sabah.com.tr", "takvim.com.tr",
    "ensonhaber.com", "mynet.com", "haberler.com", "memurlar.net",
    "ahaber.com.tr", "yenisafak.com",
}

WIKI_DOMAINS: set[str] = {"wikipedia.org"}

NEWS_TRIGGERS: set[str] = {
    "haber", "news", "son dakika", "breaking", "gündem",
    "olay", "oluyor", "açıklama", "canlı", "yayın",
    "istifa", "seçim", "ziyaret", "görüşme", "anlaşma",
}

TURKISH_CHARS: set[str] = set("çğıöşüÇĞİÖŞÜ")

TURKISH_LEXICON: set[str] = {
    "bir", "ve", "bu", "ile", "için", "olarak", "olan", "onun",
    "en", "da", "de", "daha", "veya", "ama", "ancak", "kadar",
    "gibi", "sonra", "önce", "yani", "çok", "kendi", "her",
    "tüm", "hiç", "biraz", "hem", "ya", "ise", "diye",
    "yeni", "parti", "haber", "gündem", "son", "dakika", "canlı",
    "olay", "seçim", "istifa", "ziyaret", "açıklama", "görüşme",
    "anlaşma", "başbakan", "cumhurbaşkanı", "bakan", "bakanlık",
    "meclis", "mahkeme", "karar", "savaş", "barış", "ekonomi",
    "siyaset", "spor", "sağlık", "eğitim", "kültür", "sanat",
    "dünya", "türkiye", "Türkiye", "istanbul", "ankara", "izmir",
    "adalet", "kalkınma", "partisi", "tüm", "üzerine", "altında",
}

TR_STOP_WORDS: set[str] = {
    "bir", "ve", "ile", "bu", "için", "olarak", "olan", "onun",
    "en", "da", "de", "daha", "veya", "ama", "ancak", "kadar",
    "gibi", "sonra", "önce", "yani", "çok", "kendi", "her",
    "tüm", "hiç", "biraz", "hem", "ya", "ise", "diye",
}

EN_STOP_WORDS: set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "by", "with", "from", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "can", "could", "may", "might", "shall", "should",
    "this", "that", "these", "those", "it", "its", "they", "them",
    "their", "we", "us", "our", "you", "your", "he", "she", "him",
    "her", "his", "not", "no", "nor", "so", "if", "then", "than",
}
