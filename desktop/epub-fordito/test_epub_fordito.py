"""Tesztek a szimulált fordítóval (EPUB_FORDITO_MOCK=1) – netet nem használnak."""
import io
import os
import sys
import urllib.error
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import epub_fordito as ef  # noqa: E402

CHAPTER = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>One</title></head>
<body><section epub:type="chapter"><h1>Chapter&nbsp;One</h1>
<p class="first">"Hello," she said, <em>very</em> <strong>quietly</strong>.<br/>Then she left.</p>
<div class="box"><p>Second <a href="ch2.xhtml#x">paragraph</a> with a note<sup>1</sup>.</p></div>
<p><img src="../images/pic.png" alt="pic"/></p>
<pre>code stays</pre>
</section></body></html>'''


def make_epub(path):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip')
        z.writestr('META-INF/container.xml', '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OPS/book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr('OPS/book.opf', '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
                   '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">x</dc:identifier><dc:title>The Test Book</dc:title><dc:language>en</dc:language></metadata>'
                   '<manifest><item id="c1" href="text/ch1.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="text/nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
                   '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="img" href="images/pic.png" media-type="image/png"/></manifest>'
                   '<spine toc="ncx"><itemref idref="c1"/></spine></package>')
        z.writestr('OPS/text/ch1.xhtml', CHAPTER)
        z.writestr('OPS/text/nav.xhtml', '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body>'
                   '<nav epub:type="toc"><ol><li><a href="ch1.xhtml">Chapter One</a></li></ol></nav></body></html>')
        z.writestr('OPS/toc.ncx', '<?xml version="1.0"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><docTitle><text>The Test Book</text></docTitle>'
                   '<navMap><navPoint id="n1" playOrder="1"><navLabel><text>Chapter One</text></navLabel><content src="text/ch1.xhtml"/></navPoint></navMap></ncx>')
        z.writestr('OPS/images/pic.png', b'\x89PNG fake')


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv('EPUB_FORDITO_MOCK', '1')
    monkeypatch.setenv('APPDATA', str(tmp_path / 'appdata'))


def read(z, name):
    return z.read(name).decode('utf-8')


def test_hu_quotes():
    st = [False]
    assert ef.hu_quotes_text('"Szia," mondta. "Gyere!"', st) == '„Szia,” mondta. „Gyere!”'
    assert ef.hu_quotes_text('„Már jó” és “angol”', [False]) == '„Már jó” és „angol”'


def test_translate_epub_keeps_structure(tmp_path):
    src = tmp_path / 'book.epub'
    make_epub(src)
    out = ef.translate_epub(str(src), 'x', log=lambda m: None)
    z = zipfile.ZipFile(out)
    assert z.infolist()[0].filename == 'mimetype' and z.infolist()[0].compress_type == zipfile.ZIP_STORED
    ch = read(z, 'OPS/text/ch1.xhtml')
    assert '<!DOCTYPE html' in ch
    assert '[HU] „Hello,” she said, <em>very</em> <strong>quietly</strong>.<br/>Then she left.' in ch
    assert '<a href="ch2.xhtml#x">paragraph</a>' in ch and '<sup>1</sup>' in ch
    assert '<pre>code stays</pre>' in ch                 # kód nem fordul
    assert '[HU] Chapter One' in ch or '[HU] Chapter&#160;One' in ch
    assert 'lang="hu"' in ch
    assert '<a href="ch1.xhtml">[HU] Chapter One</a>' in read(z, 'OPS/text/nav.xhtml')
    assert '[HU] Chapter One' in read(z, 'OPS/toc.ncx')
    opf = read(z, 'OPS/book.opf')
    assert '<dc:language>hu</dc:language>' in opf and '[HU] The Test Book' in opf
    assert z.read('OPS/images/pic.png') == b'\x89PNG fake'
    # a kimenet újra beolvasható és szövegként kinyerhető
    ef.Epub(out)
    txt = open(ef.epub_to_txt(out, log=lambda m: None), encoding='utf-8').read()
    assert '[HU] „Hello,” she said, very quietly.\nThen she left.' in txt


def test_cache_resumes_without_resending(tmp_path, monkeypatch):
    src = tmp_path / 'book.epub'
    make_epub(src)
    calls = []
    orig = ef.MockTranslator.translate
    monkeypatch.setattr(ef.MockTranslator, 'translate', lambda self, t: calls.append(len(t)) or orig(self, t))
    ef.translate_epub(str(src), 'x', log=lambda m: None)
    first = sum(calls)
    assert first > 0
    calls.clear()
    ef.translate_epub(str(src), 'x', log=lambda m: None)
    assert sum(calls) == 0


def test_txt_roundtrip(tmp_path):
    src = tmp_path / 'novel.txt'
    src.write_text('My Novel\n\n\n\nChapter 1\n\nIt was a dark night.\nThe rain fell.\n\nShe waited.\n\n\n\nChapter 2\n\n"Run!" he said.\n', encoding='utf-8')
    ep = ef.txt_to_epub(str(src), log=lambda m: None)
    z = zipfile.ZipFile(ep)
    assert z.infolist()[0].filename == 'mimetype'
    e = ef.Epub(ep)
    assert e.title() == 'My Novel'
    assert len(e.spine) == 3                              # címlap + 2 fejezet
    ch1 = read(z, 'OEBPS/chap001.xhtml')
    assert '<h2>Chapter 1</h2>' in ch1 and 'It was a dark night.<br/>The rain fell.' in ch1
    assert 'Chapter 2' in read(z, 'OEBPS/nav.xhtml')
    back = open(ef.epub_to_txt(ep, log=lambda m: None), encoding='utf-8').read()
    assert 'Chapter 1\n\nIt was a dark night.\nThe rain fell.\n\nShe waited.' in back
    assert '\n\n\n\nChapter 2\n\n"Run!" he said.' in back


def test_chapter_headings_without_blank_lines(tmp_path):
    src = tmp_path / 'h.txt'
    src.write_text('Chapter 1\nText one.\n\nMore.\nChapter 2\nText two.\n', encoding='utf-8')
    e = ef.Epub(ef.txt_to_epub(str(src), log=lambda m: None))
    assert len(e.spine) == 3


def test_translate_txt(tmp_path):
    src = tmp_path / 'a.txt'
    src.write_text('First para.\nSame para.\n\n"Quote" here.\n', encoding='utf-8')
    out = open(ef.translate_txt(str(src), 'x', log=lambda m: None), encoding='utf-8').read()
    assert out == '[HU] First para.\nSame para.\n\n[HU] „Quote” here.\n'


def test_cp1250_text(tmp_path):
    src = tmp_path / 'c.txt'
    src.write_bytes('Árvíztűrő tükörfúrógép\n\nSzöveg.'.encode('cp1250'))
    z = zipfile.ZipFile(ef.txt_to_epub(str(src), log=lambda m: None))
    assert '<h2>Árvíztűrő tükörfúrógép</h2>' in read(z, 'OEBPS/chap001.xhtml')


def test_deepl_errors(monkeypatch):
    d = ef.DeepL('abc:fx')
    assert d.base == 'https://api-free.deepl.com'
    assert ef.DeepL('abc').base == 'https://api.deepl.com'

    def raise_code(code):
        def f(*a, **k):
            raise urllib.error.HTTPError('u', code, 'x', {}, io.BytesIO(b'{}'))
        return f
    monkeypatch.setattr(ef.urllib.request, 'urlopen', raise_code(456))
    with pytest.raises(ef.QuotaError):
        d.translate(['a'])
    monkeypatch.setattr(ef.urllib.request, 'urlopen', raise_code(403))
    with pytest.raises(ef.TranslateError, match='kulcs'):
        d.translate(['a'])


def test_quota_keeps_partial_cache(tmp_path, monkeypatch):
    src = tmp_path / 'book.epub'
    make_epub(src)
    n = {'c': 0}

    def flaky(self, texts):
        n['c'] += 1
        if n['c'] > 1:
            raise ef.QuotaError('elfogyott')
        return ['[HU] ' + t for t in texts]
    monkeypatch.setattr(ef.MockTranslator, 'translate', flaky)
    monkeypatch.setattr(ef, 'run_batches', ef.run_batches)
    orig_batches = ef.run_batches

    def small(tr, cache, texts, progress, log, stop):   # egyesével küldjük, hogy legyen részleges eredmény
        for t in texts:
            orig_batches(tr, cache, [t], progress, log, stop)
    monkeypatch.setattr(ef, 'run_batches', small)
    with pytest.raises(ef.QuotaError):
        ef.translate_epub(str(src), 'x', log=lambda m: None)
    assert len(ef.Cache(str(src)).data) == 1


def test_cli(tmp_path):
    src = tmp_path / 'c.txt'
    src.write_text('Hello world.\n', encoding='utf-8')
    assert ef.main(['to-epub', str(src), '--title', 'T']) == 0
    assert ef.main(['translate', str(src)]) == 0
    assert (tmp_path / 'c - magyar.txt').read_text(encoding='utf-8') == '[HU] Hello world.\n'
    assert ef.main(['to-txt', str(tmp_path / 'nincs.epub')]) == 1
