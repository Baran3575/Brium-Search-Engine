from __future__ import annotations

from brium.rank.classifier import (
    classify, detect_lang, is_stop_word,
    domain_tier, domain_authority, url_depth_penalty,
)
from brium.rank.booster import (
    entity_boost, freshness_boost, lang_boost, title_start_boost,
)
from brium.rank.diversifier import diversify
from brium.rank.scorer import make_snippet
from brium.base.types import SearchResult


def test_classify():
    assert classify("son dakika deprem") == "news"
    assert classify("yeni parti") == "general"
    assert classify("Barack Obama") == "entity"
    assert classify("hello world") == "general"


def test_detect_lang():
    assert detect_lang("yeni parti") == "tr"
    assert detect_lang("hello world") == "en"
    assert detect_lang("türkiye") == "tr"
    assert detect_lang("merhaba dünya") == "tr"


def test_is_stop_word():
    assert is_stop_word("bir") is True
    assert is_stop_word("the") is True
    assert is_stop_word("ve") is True
    assert is_stop_word("parti") is False
    assert is_stop_word("hello") is False


def test_domain_tier():
    assert domain_tier("sozcu.com.tr") == 2
    assert domain_tier("www.sozcu.com.tr") == 2
    assert domain_tier("tr.wikipedia.org") == 1
    assert domain_tier("en.wikipedia.org") == 1
    assert domain_tier("example.com") == 0


def test_domain_authority():
    assert domain_authority("sozcu.com.tr") >= 1.3
    assert domain_authority("en.wikipedia.org") >= 1.2
    assert domain_authority("example.com") == 1.0
    assert domain_authority("example.com", incoming_links=10) > 1.0


def test_url_depth_penalty():
    assert url_depth_penalty("https://example.com/") == 1.0
    assert url_depth_penalty("https://example.com/a") == 1.0
    assert 0.9 < url_depth_penalty("https://example.com/a/b") < 1.0
    assert 0.8 < url_depth_penalty("https://example.com/a/b/c") < 0.95
    deep = url_depth_penalty("https://example.com/" + "/".join(["a"] * 20))
    assert deep == 0.7


def test_entity_boost():
    assert entity_boost("yeni parti", "Yeni Parti Kuruldu", "") == 3.0
    assert entity_boost("yeni parti partisi", "Yeni Parti Kuruldu", "") == 2.5
    assert entity_boost("yeni parti", "Baslik", "yeni parti aciklamasi") == 2.0
    assert entity_boost("yeni parti", "Baslik", "") == 1.0


def test_freshness_boost():
    assert freshness_boost(0, 7) == 1.0
    assert freshness_boost(7, 7) == 0.5
    assert freshness_boost(14, 7) == 1.0 / 3.0
    assert freshness_boost(0, 90) == 1.0


def test_lang_boost():
    assert lang_boost("tr", "tr") == 1.3
    assert lang_boost("en", "tr") == 1.0
    assert lang_boost("en", "en") == 1.3


def test_title_start_boost():
    assert title_start_boost("Parti lideri konustu", "parti") == 1.2
    assert title_start_boost("Baslik", "parti") == 1.0


def test_make_snippet():
    text = "Bugün yeni parti kuruldu ve toplumda büyük heyecan yarattı"
    s = make_snippet(text, "yeni parti")
    assert "yeni parti" in s
    assert make_snippet("", "test") == ""
    assert make_snippet("hello world", "xyz") == "hello world"


def test_diversify():
    r1 = SearchResult("https://a.com/p1", "A1", 10.0)
    r2 = SearchResult("https://b.com/p2", "B1", 9.0)
    r3 = SearchResult("https://a.com/p3", "A2", 8.0)
    d = diversify([r1, r2, r3])
    assert len(d) == 3
    assert d[0].url == "https://a.com/p1"
    assert d[1].url == "https://b.com/p2"
    assert d[2].url == "https://a.com/p3"
