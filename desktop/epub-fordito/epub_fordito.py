#!/usr/bin/env python3
"""EPUB Fordító – EPUB ↔ TXT átalakítás és angol → magyar fordítás (DeepL).

Ablakos program (paraméter nélkül indítva), de parancssorból is használható:
    epub_fordito.py to-txt   konyv.epub
    epub_fordito.py to-epub  konyv.txt [--title "Cím"] [--author "Szerző"] [--lang hu]
    epub_fordito.py translate konyv.epub|konyv.txt [--key DEEPL_KULCS]
    epub_fordito.py usage    [--key DEEPL_KULCS]

A fordítás a könyv szerkezetét megtartja: a bekezdéseket egyenként (a dőlt, félkövér stb.
jelölésekkel együtt) küldi a DeepL-nek, a fejezetek, képek és stílusok változatlanok maradnak.
A már lefordított bekezdéseket elmenti, így ha megszakad vagy elfogy a havi keret,
legközelebb onnan folytatja (és nem fizetsz kétszer ugyanazért a szövegért).
"""
import argparse
import hashlib
import html
import json
import os
import posixpath
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile

from lxml import etree

APP = 'EpubFordito'
# Ablakos (konzol nélküli) .exe-ben nincs stdout/stderr – a kiírások ne okozzanak hibát
for _n in ('stdout', 'stderr'):
    if getattr(sys, _n) is None:
        setattr(sys, _n, open(os.devnull, 'w', encoding='utf-8'))
    elif hasattr(getattr(sys, _n), 'reconfigure'):
        getattr(sys, _n).reconfigure(errors='replace')
XHTML_NS = 'http://www.w3.org/1999/xhtml'
EPUB_NS = 'http://www.idpf.org/2007/ops'
OPF_NS = 'http://www.idpf.org/2007/opf'
DC_NS = 'http://purl.org/dc/elements/1.1/'
NCX_NS = 'http://www.daisy.org/z3986/2005/ncx/'
CONT_NS = 'urn:oasis:names:tc:opendocument:xmlns:container'
PARSER = etree.XMLParser(recover=True, resolve_entities=False, huge_tree=True)

# Ezeket az elemeket fordítjuk / írjuk ki bekezdésként (ha nincs bennük további ilyen elem)
UNIT_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'dt', 'dd', 'td', 'th', 'caption', 'figcaption', 'blockquote', 'div'}
CONTAINER_TAGS = UNIT_TAGS | {'section', 'article', 'aside', 'header', 'footer', 'nav', 'table', 'ul', 'ol', 'dl', 'figure', 'pre'}
SKIP_TAGS = {'pre', 'code', 'script', 'style', 'math', 'svg'}


class TranslateError(Exception):
    pass


class QuotaError(TranslateError):
    pass


# ---------- Segédfüggvények ----------
def local(el):
    return etree.QName(el).localname if isinstance(el.tag, str) else ''


_XML_ENT = {'amp', 'lt', 'gt', 'quot', 'apos'}


def fix_entities(s):
    """HTML-entitások (pl. &nbsp;) számmá alakítása, hogy XML-ként is beolvasható legyen."""
    def rep(m):
        name = m.group(1)
        if name in _XML_ENT:
            return m.group(0)
        ch = html.unescape(m.group(0))
        return '&#%d;' % ord(ch) if len(ch) == 1 else m.group(0)
    return re.sub(r'&([a-zA-Z][a-zA-Z0-9]*);', rep, s)


def parse_xml(data):
    if isinstance(data, bytes):
        data = data.decode('utf-8', errors='replace')
    data = fix_entities(data.lstrip('﻿'))
    return etree.fromstring(data.encode('utf-8'), PARSER).getroottree()


def ser(tree):
    return etree.tostring(tree, xml_declaration=True, encoding='utf-8')


def unit_elements(root):
    """A „levél” bekezdés-szintű elemek (amelyekben nincs további bekezdés) dokumentum-sorrendben."""
    body = next((e for e in root.iter() if local(e) == 'body'), root)
    out = []
    for el in body.iter():
        name = local(el)
        if name not in UNIT_TAGS:
            continue
        if any(local(a) in SKIP_TAGS for a in el.iterancestors()):
            continue
        if any(local(d) in CONTAINER_TAGS for d in el.iterdescendants()):
            continue
        if not re.search(r'\w', ''.join(el.itertext())):
            continue
        # <li><a>…</a></li> jellegű elemnél a belső elemet fordítjuk, így a szöveg biztosan a linken belül marad
        while len(el) == 1 and not (el.text or '').strip() and not (el[0].tail or '').strip() and local(el[0]) not in ('img', 'br') and re.search(r'\w', ''.join(el[0].itertext())):
            el = el[0]
        out.append(el)
    return out


def inner_html(el):
    parts = [html.escape(el.text or '', quote=False)]
    for ch in el:
        parts.append(etree.tostring(ch, encoding='unicode', with_tail=True))
    s = ''.join(parts)
    return s.replace(' xmlns="%s"' % XHTML_NS, '')


def set_inner(el, frag, fallback_text):
    """A lefordított HTML-darab visszahelyezése; ha nem olvasható be, a sima szöveget írjuk be."""
    try:
        wrap = etree.fromstring(('<w xmlns="%s" xmlns:epub="%s">%s</w>' % (XHTML_NS, EPUB_NS, fix_entities(frag))).encode('utf-8'), PARSER)
        if wrap is None or len(''.join(wrap.itertext()).strip()) < 0.5 * len(fallback_text.strip()):
            raise ValueError('hiányos')
    except Exception:
        for ch in list(el):
            el.remove(ch)
        el.text = fallback_text
        return
    for ch in list(el):
        el.remove(ch)
    el.text = wrap.text
    for ch in list(wrap):
        el.append(ch)


def strip_tags(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s))


# Magyar idézőjelek: "…" / “…” → „…”
_Q = re.compile('["“”„]')


def hu_quotes_text(s, state):
    def rep(m):
        c = m.group(0)
        if c == '„':
            state[0] = True
            return c
        state[0] = not state[0]
        return '„' if state[0] else '”'
    return _Q.sub(rep, s) if s else s


def hu_quotes_el(el):
    state = [False]

    def walk(n):
        if isinstance(n.tag, str):
            n.text = hu_quotes_text(n.text, state)
        for ch in n:
            walk(ch)
            ch.tail = hu_quotes_text(ch.tail, state)
    walk(el)


def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists('%s (%d)%s' % (base, i, ext)):
        i += 1
    return '%s (%d)%s' % (base, i, ext)


def config_dir():
    base = os.environ.get('APPDATA') or os.path.join(os.path.expanduser('~'), '.config')
    d = os.path.join(base, APP)
    os.makedirs(d, exist_ok=True)
    return d


def load_config():
    try:
        with open(os.path.join(config_dir(), 'config.json'), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    with open(os.path.join(config_dir(), 'config.json'), 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)


# ---------- EPUB beolvasása ----------
class Epub:
    def __init__(self, path):
        self.path = path
        self.zf = zipfile.ZipFile(path)
        cont = parse_xml(self.zf.read('META-INF/container.xml'))
        rf = cont.getroot().find('.//{%s}rootfile' % CONT_NS)
        if rf is None:
            raise ValueError('Ez nem érvényes EPUB (hiányzik a rootfile).')
        self.opf_path = rf.get('full-path')
        self.opf_dir = posixpath.dirname(self.opf_path)
        self.opf = parse_xml(self.zf.read(self.opf_path))
        self.manifest = {}
        for it in self.opf.getroot().iter('{%s}item' % OPF_NS):
            self.manifest[it.get('id')] = (self.href(it.get('href')), it.get('media-type', ''), it.get('properties', ''))
        self.spine = []
        for ir in self.opf.getroot().iter('{%s}itemref' % OPF_NS):
            m = self.manifest.get(ir.get('idref'))
            if m and m[1] in ('application/xhtml+xml', 'text/html'):
                self.spine.append(m[0])

    def href(self, h):
        from urllib.parse import unquote
        return posixpath.normpath(posixpath.join(self.opf_dir, unquote(h.split('#')[0])))

    def content_docs(self):
        """Minden XHTML (a gerincben lévők elöl, sorrendben), plusz a tartalomjegyzék (nav)."""
        seen, out = set(), []
        for p in self.spine + [m[0] for m in self.manifest.values() if m[1] in ('application/xhtml+xml', 'text/html')]:
            if p not in seen and p in self.zf.namelist():
                seen.add(p)
                out.append(p)
        return out

    def ncx(self):
        for p, mt, _ in self.manifest.values():
            if mt == 'application/x-dtbncx+xml' and p in self.zf.namelist():
                return p
        return None

    def title(self):
        t = self.opf.getroot().find('.//{%s}title' % DC_NS)
        return (t.text or '').strip() if t is not None else ''


# ---------- EPUB → TXT ----------
def epub_to_txt(src, dst=None, log=print):
    ep = Epub(src)
    chapters = []
    for p in ep.spine:
        if p not in ep.zf.namelist():
            continue
        root = parse_xml(ep.zf.read(p)).getroot()
        paras = []
        for el in unit_elements(root):
            for br in el.iter('{%s}br' % XHTML_NS):
                br.tail = '\n' + (br.tail or '')
            t = ''.join(el.itertext())
            t = '\n'.join(re.sub(r'[ \t\r\f\v ]+', ' ', ln).strip() for ln in t.split('\n')).strip()
            if t:
                paras.append(t)
        if paras:
            chapters.append('\n\n'.join(paras))
    if not chapters:
        raise ValueError('Nem találtam szöveget ebben az EPUB-ban.')
    title = ep.title()
    text = ((title + '\n\n\n\n') if title and not chapters[0].startswith(title) else '') + '\n\n\n\n'.join(chapters) + '\n'
    dst = dst or unique_path(os.path.splitext(src)[0] + '.txt')
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(text)
    log('✅ Kész: %d fejezet, %d karakter → %s' % (len(chapters), len(text), dst))
    return dst


# ---------- TXT → EPUB ----------
CHAP_RE = re.compile(r'^\s*(#+\s+.+|(chapter|fejezet|prológus|prologue|epilógus|epilogue|part|book|könyv)\b.{0,70}|\d{1,3}\.\s*(fejezet|rész)\b.{0,70}|[IVXLC]{1,7}\.?\s*$)', re.I)


def read_text(path):
    raw = open(path, 'rb').read()
    for enc in ('utf-8-sig', 'cp1250', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace')


def split_chapters(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n').strip('\n')
    chunks = [c.strip('\n') for c in re.split(r'\n[ \t]*\n[ \t]*\n[ \t]*\n+', text) if c.strip()]
    if len(chunks) <= 1:
        # Nincs üres-soros fejezethatár: fejezetcímek alapján
        lines, cur, chunks = text.split('\n'), [], []
        for ln in lines:
            if CHAP_RE.match(ln) and len(ln.strip()) <= 80 and any(x.strip() for x in cur):
                chunks.append('\n'.join(cur).strip('\n'))
                cur = []
            cur.append(ln)
        chunks.append('\n'.join(cur).strip('\n'))
        chunks = [c for c in chunks if c.strip()]
    return chunks


def paragraphs(chunk):
    paras = [p for p in re.split(r'\n[ \t]*\n', chunk) if p.strip()]
    lines = [ln for p in paras for ln in p.split('\n') if ln.strip()]
    # Tördelt (fix szélességű) szöveg: a sorvégeket szóközzé alakítjuk
    wrapped = len(lines) > 20 and sum(1 for ln in lines if 55 <= len(ln) <= 90) > 0.6 * len(lines)
    out = []
    for p in paras:
        ls = [ln.strip() for ln in p.split('\n') if ln.strip()]
        out.append((' '.join(ls), False) if wrapped else ('\n'.join(ls), True))
    return out


def xhtml_page(title, body, lang):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="%s" xmlns:epub="%s" lang="%s" xml:lang="%s"><head><meta charset="utf-8"/><title>%s</title>'
            '<link rel="stylesheet" type="text/css" href="style.css"/></head><body>%s</body></html>'
            % (XHTML_NS, EPUB_NS, lang, lang, html.escape(title), body))


CSS = ('body{font-family:serif;line-height:1.5;margin:0 5%}h1,h2{text-align:center;margin:2em 0 1em;page-break-before:always}'
       'p{text-indent:1.4em;margin:0 0 .3em;text-align:justify}h1+p,h2+p{text-indent:0}.title{font-size:2em;margin-top:30%}')


def txt_to_epub(src, dst=None, title=None, author=None, lang='hu', log=print):
    text = read_text(src)
    chunks = split_chapters(text)
    if not chunks:
        raise ValueError('Üres a szövegfájl.')
    book_title = title
    if not book_title:
        if len(chunks) > 1 and len(chunks[0]) <= 120 and '\n' not in chunks[0].strip():
            book_title = chunks.pop(0).strip()
        else:
            book_title = os.path.splitext(os.path.basename(src))[0]
    author = author or 'Ismeretlen szerző'
    uid = 'urn:uuid:%s' % uuid.uuid4()
    chapters = []
    for i, ch in enumerate(chunks, 1):
        paras = paragraphs(ch)
        head = paras[0][0] if paras else ''
        short = head and len(head) <= 80 and '\n' not in head
        if short and (CHAP_RE.match(head) or not head.rstrip('"”\'»').endswith(('.', ',', ';', '!', '?', '…', ':'))):
            ctitle, paras = head.lstrip('#').strip(), paras[1:]
        else:
            ctitle = '%d. fejezet' % i if len(chunks) > 1 else book_title
        body = '<h2>%s</h2>' % html.escape(ctitle)
        for p, keep in paras:
            body += '<p>%s</p>' % (html.escape(p).replace('\n', '<br/>') if keep else html.escape(p))
        chapters.append(('chap%03d.xhtml' % i, ctitle, xhtml_page(ctitle, body, lang)))
    dst = dst or unique_path(os.path.splitext(src)[0] + '.epub')
    title_page = xhtml_page(book_title, '<h1 class="title">%s</h1><p style="text-align:center;text-indent:0">%s</p>' % (html.escape(book_title), html.escape(author)), lang)
    nav = xhtml_page('Tartalom', '<nav epub:type="toc" id="toc"><h1>Tartalom</h1><ol>%s</ol></nav>' % ''.join(
        '<li><a href="%s">%s</a></li>' % (f, html.escape(t)) for f, t, _ in chapters), lang)
    ncx = ('<?xml version="1.0" encoding="utf-8"?><ncx xmlns="%s" version="2005-1"><head><meta name="dtb:uid" content="%s"/></head>'
           '<docTitle><text>%s</text></docTitle><navMap>%s</navMap></ncx>' % (NCX_NS, uid, html.escape(book_title), ''.join(
               '<navPoint id="np%d" playOrder="%d"><navLabel><text>%s</text></navLabel><content src="%s"/></navPoint>' % (i, i, html.escape(t), f)
               for i, (f, t, _) in enumerate(chapters, 1))))
    items = ''.join('<item id="c%d" href="%s" media-type="application/xhtml+xml"/>' % (i, f) for i, (f, _, _) in enumerate(chapters, 1))
    refs = ''.join('<itemref idref="c%d"/>' % i for i in range(1, len(chapters) + 1))
    opf = ('<?xml version="1.0" encoding="utf-8"?><package xmlns="%s" version="3.0" unique-identifier="uid" xml:lang="%s">'
           '<metadata xmlns:dc="%s"><dc:identifier id="uid">%s</dc:identifier><dc:title>%s</dc:title><dc:creator>%s</dc:creator>'
           '<dc:language>%s</dc:language><meta property="dcterms:modified">%s</meta></metadata>'
           '<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
           '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="css" href="style.css" media-type="text/css"/>'
           '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>%s</manifest>'
           '<spine toc="ncx"><itemref idref="title"/>%s</spine></package>'
           % (OPF_NS, lang, DC_NS, uid, html.escape(book_title), html.escape(author), lang, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), items, refs))
    with zipfile.ZipFile(dst, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        zc = zipfile.ZIP_DEFLATED
        z.writestr('META-INF/container.xml', '<?xml version="1.0" encoding="utf-8"?><container version="1.0" xmlns="%s"><rootfiles>'
                   '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>' % CONT_NS, zc)
        z.writestr('OEBPS/content.opf', opf, zc)
        z.writestr('OEBPS/nav.xhtml', nav, zc)
        z.writestr('OEBPS/toc.ncx', ncx, zc)
        z.writestr('OEBPS/style.css', CSS, zc)
        z.writestr('OEBPS/title.xhtml', title_page, zc)
        for f, _, page in chapters:
            z.writestr('OEBPS/' + f, page, zc)
    log('✅ Kész: „%s”, %d fejezet → %s' % (book_title, len(chapters), dst))
    return dst


# ---------- DeepL ----------
class DeepL:
    def __init__(self, key):
        self.key = (key or '').strip()
        if not self.key:
            raise TranslateError('Nincs megadva DeepL API-kulcs.')
        self.base = 'https://api-free.deepl.com' if self.key.endswith(':fx') else 'https://api.deepl.com'

    def _req(self, path, body=None):
        data = json.dumps(body).encode('utf-8') if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method='POST' if data else 'GET',
                                     headers={'Authorization': 'DeepL-Auth-Key ' + self.key, 'Content-Type': 'application/json', 'User-Agent': APP})
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    return json.loads(r.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    raise TranslateError('A DeepL nem fogadja el a kulcsot (403). Ellenőrizd, hogy jól másoltad-e be.')
                if e.code == 456:
                    raise QuotaError('Elfogyott a havi DeepL-keret (456). A már lefordított részek mentve vannak, a keret megújulása után innen folytatható.')
                if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise TranslateError('DeepL-hiba: %s %s' % (e.code, e.read()[:200].decode('utf-8', 'replace')))
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise TranslateError('Nem érem el a DeepL-t (van internet?): %s' % e)

    def usage(self):
        u = self._req('/v2/usage')
        return u.get('character_count', 0), u.get('character_limit', 0)

    def translate(self, texts):
        r = self._req('/v2/translate', {'text': texts, 'source_lang': 'EN', 'target_lang': 'HU', 'tag_handling': 'html'})
        return [t['text'] for t in r['translations']]


class MockTranslator:
    """Teszteléshez (EPUB_FORDITO_MOCK=1): nem hív netet, csak megjelöli a szöveget."""
    def usage(self):
        return 0, 500000

    def translate(self, texts):
        return ['[HU] ' + t for t in texts]


def make_translator(key):
    return MockTranslator() if os.environ.get('EPUB_FORDITO_MOCK') else DeepL(key)


# ---------- Fordítás ----------
class Cache:
    """A már lefordított szövegdarabok (bemenet-hash → fordítás), a felhasználói mappában."""
    def __init__(self, src):
        h = hashlib.sha1(open(src, 'rb').read()).hexdigest()[:16]
        d = os.path.join(config_dir(), 'cache')
        os.makedirs(d, exist_ok=True)
        self.path = os.path.join(d, h + '.json')
        try:
            with open(self.path, encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception:
            self.data = {}

    @staticmethod
    def k(s):
        return hashlib.sha1(s.encode('utf-8')).hexdigest()

    def get(self, s):
        return self.data.get(self.k(s))

    def put(self, s, t):
        self.data[self.k(s)] = t

    def save(self):
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)
        os.replace(tmp, self.path)


def run_batches(tr, cache, texts, progress, log, stop):
    """A még le nem fordított szövegeket kötegekben (max. 50 db / ~60 000 karakter) küldi el."""
    todo = list(dict.fromkeys(t for t in texts if cache.get(t) is None))
    total = sum(len(strip_tags(t)) for t in todo)
    done_chars = 0
    if not todo:
        progress(1, 1)
        return
    log('Fordítandó: %d bekezdés, kb. %s karakter (a már lefordítottakat nem küldöm el újra).' % (len(todo), format(total, ',').replace(',', ' ')))
    i = 0
    while i < len(todo):
        if stop and stop():
            cache.save()
            raise TranslateError('Megszakítva. A már lefordított részek mentve vannak.')
        batch, size = [], 0
        while i < len(todo) and len(batch) < 50 and (size + len(todo[i]) < 60000 or not batch):
            batch.append(todo[i])
            size += len(todo[i])
            i += 1
        try:
            res = tr.translate(batch)
        except TranslateError:
            cache.save()
            raise
        for s, t in zip(batch, res):
            cache.put(s, t)
            done_chars += len(strip_tags(s))
        cache.save()
        progress(done_chars, total)


def translate_epub(src, key, dst=None, hu_quotes=True, translate_title=True, log=print, progress=lambda a, b: None, stop=None):
    ep = Epub(src)
    tr = make_translator(key)
    cache = Cache(src)
    docs = {}
    units = []
    for p in ep.content_docs():
        tree = parse_xml(ep.zf.read(p))
        docs[p] = tree
        for el in unit_elements(tree.getroot()):
            units.append((el, inner_html(el)))
    ncx_path = ep.ncx()
    ncx = parse_xml(ep.zf.read(ncx_path)) if ncx_path else None
    ncx_texts = [t for t in ncx.getroot().iter('{%s}text' % NCX_NS) if (t.text or '').strip()] if ncx is not None else []
    opf_titles = [t for t in ep.opf.getroot().iter('{%s}title' % DC_NS) if (t.text or '').strip()] if translate_title else []
    plain = [html.escape(t.text.strip(), quote=False) for t in ncx_texts + opf_titles]
    log('» „%s”: %d dokumentum, %d bekezdés' % (ep.title() or os.path.basename(src), len(docs), len(units)))
    run_batches(tr, cache, [h for _, h in units] + plain, progress, log, stop)
    # Visszaírás
    for el, h in units:
        t = cache.get(h)
        set_inner(el, t, strip_tags(t))
        if hu_quotes:
            hu_quotes_el(el)
    for t in ncx_texts + opf_titles:
        tt = strip_tags(cache.get(html.escape(t.text.strip(), quote=False)))
        t.text = hu_quotes_text(tt, [False]) if hu_quotes else tt
    root = ep.opf.getroot()
    for lg in root.iter('{%s}language' % DC_NS):
        lg.text = 'hu'
    for tree in docs.values():
        r = tree.getroot()
        if local(r) == 'html':
            r.set('lang', 'hu')
            r.set('{http://www.w3.org/XML/1998/namespace}lang', 'hu')
    dst = dst or unique_path(os.path.splitext(src)[0] + ' - magyar.epub')
    changed = {p: ser(t) for p, t in docs.items()}
    changed[ep.opf_path] = ser(ep.opf)
    if ncx is not None:
        changed[ncx_path] = ser(ncx)
    with zipfile.ZipFile(dst, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        for info in ep.zf.infolist():
            if info.filename == 'mimetype':
                continue
            z.writestr(info.filename, changed.get(info.filename, ep.zf.read(info.filename)), zipfile.ZIP_DEFLATED)
    log('✅ Kész a magyar EPUB: %s' % dst)
    return dst


def translate_txt(src, key, dst=None, hu_quotes=True, log=print, progress=lambda a, b: None, stop=None):
    text = read_text(src).replace('\r\n', '\n').replace('\r', '\n')
    parts = re.split(r'(\n[ \t]*\n)', text)
    tr = make_translator(key)
    cache = Cache(src)
    blocks = [html.escape(p.strip(), quote=False) for p in parts[::2] if p.strip()]
    log('» %s: %d bekezdés' % (os.path.basename(src), len(blocks)))
    run_batches(tr, cache, blocks, progress, log, stop)
    out = []
    for i, p in enumerate(parts):
        if i % 2 or not p.strip():
            out.append(p)
            continue
        t = strip_tags(cache.get(html.escape(p.strip(), quote=False)))
        lead, trail = re.match(r'\s*', p).group(0), re.search(r'\s*$', p).group(0)
        out.append(lead + (hu_quotes_text(t, [False]) if hu_quotes else t) + trail)
    dst = dst or unique_path(os.path.splitext(src)[0] + ' - magyar.txt')
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(''.join(out))
    log('✅ Kész a magyar szöveg: %s' % dst)
    return dst


def estimate_chars(src):
    if src.lower().endswith('.epub'):
        ep = Epub(src)
        return sum(len(''.join(el.itertext())) for p in ep.content_docs() for el in unit_elements(parse_xml(ep.zf.read(p)).getroot()))
    return len(read_text(src))


# ---------- Ablakos felület ----------
def gui():
    import queue
    import threading
    import tkinter as tk
    import webbrowser
    from tkinter import filedialog, messagebox, ttk

    cfg = load_config()
    root = tk.Tk()
    root.title('EPUB Fordító')
    root.geometry('760x600')
    root.minsize(620, 480)
    try:
        ttk.Style().theme_use('vista' if sys.platform == 'win32' else 'clam')
    except tk.TclError:
        pass
    q = queue.Queue()
    busy = {'on': False, 'stop': False}
    pad = {'padx': 10, 'pady': 4}

    ttk.Label(root, text='EPUB Fordító', font=('Segoe UI', 18, 'bold')).pack(anchor='w', padx=10, pady=(10, 0))
    ttk.Label(root, text='EPUB ↔ TXT átalakítás és angol → magyar fordítás (DeepL)').pack(anchor='w', padx=10)

    f1 = ttk.LabelFrame(root, text=' 1. Válaszd ki a fájlt (EPUB vagy TXT) ')
    f1.pack(fill='x', **pad)
    path = tk.StringVar(value=cfg.get('last', ''))
    ttk.Entry(f1, textvariable=path).pack(side='left', fill='x', expand=True, padx=6, pady=6)

    def browse():
        p = filedialog.askopenfilename(filetypes=[('E-könyv vagy szöveg', '*.epub *.txt'), ('EPUB', '*.epub'), ('Szöveg', '*.txt'), ('Minden fájl', '*.*')])
        if p:
            path.set(p)
            cfg['last'] = p
            save_config(cfg)
    ttk.Button(f1, text='Tallózás…', command=browse).pack(side='left', padx=6)

    f2 = ttk.LabelFrame(root, text=' 2. DeepL API-kulcs (csak a fordításhoz kell) ')
    f2.pack(fill='x', **pad)
    key = tk.StringVar(value=cfg.get('key', ''))
    ttk.Entry(f2, textvariable=key, show='•').pack(side='left', fill='x', expand=True, padx=6, pady=6)

    def save_key():
        cfg['key'] = key.get().strip()
        save_config(cfg)
        log('✔ Kulcs elmentve (csak ezen a gépen).')
    ttk.Button(f2, text='Mentés', command=save_key).pack(side='left', padx=3)

    def check_usage():
        k = key.get()

        def job():
            used, lim = DeepL(k).usage()
            return 'ℹ️ DeepL-keret: %s / %s karakter felhasználva (még %s maradt).' % (
                format(used, ',').replace(',', ' '), format(lim, ',').replace(',', ' '), format(max(0, lim - used), ',').replace(',', ' '))
        run(job, 'Keret lekérdezése…')
    ttk.Button(f2, text='Keret', command=check_usage).pack(side='left', padx=3)
    lnk = ttk.Label(f2, text='Ingyenes kulcs ↗', foreground='#1a73e8', cursor='hand2')
    lnk.pack(side='left', padx=6)
    lnk.bind('<Button-1>', lambda e: webbrowser.open('https://www.deepl.com/pro-api'))

    f3 = ttk.LabelFrame(root, text=' 3. Mit csináljak? ')
    f3.pack(fill='x', **pad)
    quotes = tk.BooleanVar(value=cfg.get('quotes', True))
    ttitle = tk.BooleanVar(value=cfg.get('ttitle', True))
    row = ttk.Frame(f3)
    row.pack(fill='x', padx=6, pady=6)

    def need(ext=None):
        p = path.get().strip()
        if not p or not os.path.isfile(p):
            messagebox.showwarning('EPUB Fordító', 'Előbb válassz ki egy fájlt.')
            return None
        if ext and not p.lower().endswith(ext):
            messagebox.showwarning('EPUB Fordító', 'Ehhez %s fájl kell.' % ext.upper()[1:])
            return None
        return p

    def do_txt():
        p = need('.epub')
        if p:
            run(lambda: epub_to_txt(p, log=log), 'EPUB → TXT…', p)

    def do_epub():
        p = need('.txt')
        if p:
            run(lambda: txt_to_epub(p, log=log), 'TXT → EPUB…', p)

    def do_translate():
        p = need()
        if not p:
            return
        if not p.lower().endswith(('.epub', '.txt')):
            messagebox.showwarning('EPUB Fordító', 'EPUB vagy TXT fájlt tudok fordítani.')
            return
        if not key.get().strip() and not os.environ.get('EPUB_FORDITO_MOCK'):
            messagebox.showwarning('EPUB Fordító', 'Add meg a DeepL API-kulcsot (2. lépés).')
            return
        cfg.update(key=key.get().strip(), quotes=quotes.get(), ttitle=ttitle.get())
        save_config(cfg)
        try:
            est = estimate_chars(p)
        except Exception as e:
            messagebox.showerror('EPUB Fordító', str(e))
            return
        if not messagebox.askyesno('EPUB Fordító', 'A könyv kb. %s karakter. Az ingyenes DeepL-keret havi 500 000 karakter.\n'
                                   '(A korábban már lefordított részeket nem küldöm el újra.)\n\nIndulhat a fordítás?' % format(est, ',').replace(',', ' ')):
            return
        busy['stop'] = False
        # A háttérszál nem nyúlhat a Tk-változókhoz, ezért az értékeket előre kiolvassuk
        k, hq, tt = key.get(), quotes.get(), ttitle.get()
        if p.lower().endswith('.epub'):
            run(lambda: translate_epub(p, k, hu_quotes=hq, translate_title=tt, log=log, progress=prog, stop=lambda: busy['stop']), 'Fordítás…', p)
        else:
            run(lambda: translate_txt(p, k, hu_quotes=hq, log=log, progress=prog, stop=lambda: busy['stop']), 'Fordítás…', p)

    ttk.Button(row, text='EPUB → TXT', command=do_txt).pack(side='left', padx=3)
    ttk.Button(row, text='TXT → EPUB', command=do_epub).pack(side='left', padx=3)
    ttk.Button(row, text='Fordítás magyarra (EN → HU)', command=do_translate).pack(side='left', padx=3)
    stopb = ttk.Button(row, text='⏹ Leállítás', command=lambda: busy.update(stop=True), state='disabled')
    stopb.pack(side='right', padx=3)
    ttk.Checkbutton(f3, text='Magyar idézőjelek („…”)', variable=quotes).pack(anchor='w', padx=8)
    ttk.Checkbutton(f3, text='A könyv címét és a tartalomjegyzéket is fordítsa', variable=ttitle).pack(anchor='w', padx=8, pady=(0, 6))

    bar = ttk.Progressbar(root, mode='determinate', maximum=1000)
    bar.pack(fill='x', **pad)
    status = ttk.Label(root, text='Kész.')
    status.pack(anchor='w', padx=10)
    out = tk.Text(root, height=10, wrap='word', font=('Consolas', 10))
    out.pack(fill='both', expand=True, padx=10, pady=(4, 10))

    def log(msg):
        q.put(('log', msg))

    def prog(a, b):
        q.put(('prog', (a, b)))

    def run(fn, label, src=None):
        if busy['on']:
            return
        busy['on'] = True
        stopb.config(state='normal')
        status.config(text=label)
        bar.config(mode='indeterminate')
        bar.start(12)

        def worker():
            try:
                res = fn()
                q.put(('done', res))
            except Exception as e:
                q.put(('err', e))
        threading.Thread(target=worker, daemon=True).start()

    def pump():
        try:
            while True:
                kind, v = q.get_nowait()
                if kind == 'log':
                    out.insert('end', v + '\n')
                    out.see('end')
                elif kind == 'prog':
                    a, b = v
                    bar.stop()
                    bar.config(mode='determinate', value=int(1000 * a / max(1, b)))
                    status.config(text='Fordítás… %d%%' % (100 * a / max(1, b)))
                else:
                    busy['on'] = False
                    stopb.config(state='disabled')
                    bar.stop()
                    bar.config(mode='determinate', value=1000 if kind == 'done' else 0)
                    if kind == 'done':
                        status.config(text='Kész.')
                        if isinstance(v, str) and v.startswith('ℹ️'):
                            out.insert('end', v + '\n')
                            out.see('end')
                        elif isinstance(v, str) and os.path.exists(v):
                            if messagebox.askyesno('EPUB Fordító', 'Kész!\n\n%s\n\nMegnyissam a mappát?' % v):
                                folder = os.path.dirname(os.path.abspath(v))
                                if sys.platform == 'win32':
                                    os.startfile(folder)
                                else:
                                    webbrowser.open('file://' + folder)
                    else:
                        status.config(text='Hiba.')
                        out.insert('end', '❌ %s\n' % v)
                        out.see('end')
                        messagebox.showerror('EPUB Fordító', str(v))
        except queue.Empty:
            pass
        root.after(100, pump)
    pump()
    log('Szia! Válassz egy EPUB vagy TXT fájlt, aztán egy műveletet.')
    root.mainloop()


# ---------- Parancssor ----------
def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        gui()
        return 0
    ap = argparse.ArgumentParser(prog='epub_fordito', description='EPUB ↔ TXT és angol → magyar fordítás (DeepL)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('to-txt')
    a.add_argument('file')
    a.add_argument('-o', '--out')
    b = sub.add_parser('to-epub')
    b.add_argument('file')
    b.add_argument('-o', '--out')
    b.add_argument('--title')
    b.add_argument('--author')
    b.add_argument('--lang', default='hu')
    c = sub.add_parser('translate')
    c.add_argument('file')
    c.add_argument('-o', '--out')
    c.add_argument('--key')
    c.add_argument('--no-quotes', action='store_true')
    c.add_argument('--keep-title', action='store_true')
    d = sub.add_parser('usage')
    d.add_argument('--key')
    ns = ap.parse_args(argv)
    key = getattr(ns, 'key', None) or os.environ.get('DEEPL_API_KEY') or load_config().get('key', '')
    try:
        if ns.cmd == 'to-txt':
            epub_to_txt(ns.file, ns.out)
        elif ns.cmd == 'to-epub':
            txt_to_epub(ns.file, ns.out, ns.title, ns.author, ns.lang)
        elif ns.cmd == 'translate':
            bar = lambda x, y: print('\r  %d%%' % (100 * x / max(1, y)), end='', flush=True)
            if ns.file.lower().endswith('.epub'):
                translate_epub(ns.file, key, ns.out, not ns.no_quotes, not ns.keep_title, progress=bar)
            else:
                translate_txt(ns.file, key, ns.out, not ns.no_quotes, progress=bar)
        else:
            used, lim = make_translator(key).usage()
            print('DeepL-keret: %d / %d karakter' % (used, lim))
    except (TranslateError, ValueError, zipfile.BadZipFile, OSError) as e:
        print('Hiba:', e, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
