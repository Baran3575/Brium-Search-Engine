from __future__ import annotations

from brium.crawl.parser import parse_html
from brium.base.types import Page


def test_parse_html_basic():
    html = "<html><head><title>Test</title></head><body><p>hello world</p></body></html>"
    page = parse_html("http://example.com", html)
    assert page is not None
    assert page.title == "Test"
    assert "hello world" in page.text
    assert page.url == "http://example.com"


def test_parse_html_strips_scripts():
    html = "<html><body><script>alert('xss')</script><p>content</p></body></html>"
    page = parse_html("http://example.com", html)
    assert page is not None
    assert "alert" not in page.text
    assert "content" in page.text


def test_parse_html_headings():
    html = """
    <html><body>
        <h1>Main Title</h1>
        <h2>Section</h2>
        <h3>Subsection</h3>
        <p>text</p>
    </body></html>
    """
    page = parse_html("http://example.com", html)
    assert page is not None
    assert "Main Title" in page.headings
    assert "Section" in page.headings
    assert "Subsection" in page.headings


def test_parse_html_links():
    html = """
    <html><body>
        <a href="/page1">Link 1</a>
        <a href="http://other.com/page2">Link 2</a>
        <a href="javascript:void(0)">Bad</a>
    </body></html>
    """
    page = parse_html("http://example.com", html)
    assert page is not None
    assert "http://example.com/page1" in page.links
    assert "http://other.com/page2" in page.links
    assert not any("javascript" in l for l in page.links)


def test_parse_html_no_title():
    html = "<html><body><p>no title</p></body></html>"
    page = parse_html("http://example.com", html)
    assert page is not None
    assert page.title == ""
