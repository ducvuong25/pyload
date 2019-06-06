# -*- coding: utf-8 -*-
# AUTHOR: vuolter

import mimetypes
import re
import urllib.parse

import tld
from pyload.utils.check import isiterable
from pyload.utils.struct import HeaderDict
from pyload.utils.web import format, purge
from pyload.utils.web.check import is_host, is_port, isip
from pyload.utils.web.convert import host_to_ip, ip_to_host, splitaddress


def socket(text):
    addr, port = splitaddress(text.strip())
    ip = addr if isip(addr) else host_to_ip(addr)
    if port is not None and not is_port(port):
        raise ValueError(port)
    return ip, port


def endpoint(text):
    addr, port = splitaddress(text.strip())
    host = addr if is_host(addr) else ip_to_host(addr)
    if port is not None and not is_port(port):
        raise ValueError(port)
    return host, port


# TODO: Recheck result format
def attr(text, name=None):
    pattr = r'{}\s*=\s*(["\']?)((?<=")[^"]+|(?<=\')[^\']+|[^>\s"\'][^>\s]*)\1'
    pattr = pattr.format(name or r"\w+")
    m = re.search(pattr, text, flags=re.I)
    return m.group(2) if m is not None else None


def domain(url):
    return tld.get_tld(format.url(url), fail_silently=True)


_RE_FORM = re.compile(r"(<(input|textarea).*?>)([^<]*(?=</\2)|)", flags=re.I | re.S)


def _extract_inputs(form):
    taginputs = {}
    for inputtag in _RE_FORM.finditer(purge.comments(form.group("CONTENT"))):
        tagname = attr(inputtag.group(1), "name")
        if not tagname:
            continue
        tagvalue = attr(inputtag.group(1), "value")
        taginputs[tagname] = tagvalue or inputtag.group(3) or ""
    return taginputs


def _same_inputs(taginputs, inputs):
    for key, value in inputs.items():
        if key not in taginputs:
            return False
        tagvalue = taginputs[key]
        if hasattr(value, "search") and re.match(value, tagvalue):
            continue
        elif isiterable(value) and tagvalue in value:
            continue
        elif tagvalue == value:
            continue
        return False
    return True


def form(text, name=None, inputs=None):
    pattr = r"(?P<TAG><form[^>]*{}.*?>)(?P<CONTENT>.*?)</?(form|body|html).*?>"
    pattr = pattr.format(name or "")
    for form in re.finditer(pattr, text, flags=re.I | re.S):
        taginputs = _extract_inputs(form)
        formaction = attr(form.group("TAG"), "action")
        # Check input attributes
        if not inputs or _same_inputs(taginputs, inputs):
            return formaction, taginputs  # Passed attribute check
    return None, {}  # No matching form found


_RE_HEADER = re.compile(r" *(?P<key>.+?) *: *(?P<value>.+?) *\r?\n")

# TODO: Rewrite...


def header(text):
    hdict = HeaderDict()
    for key, value in _RE_HEADER.findall(text):
        key = key.lower()
        if key not in hdict:
            hdict[key] = value
        else:
            header_key = hdict.get(key)
            if isinstance(header_key, list):
                header_key.append(value)
            else:
                hdict[key] = [header_key, value]
    return hdict


def mime(text, strict=False):
    DEFAULT_MIMETYPE = "application/octet-stream"
    mimetype = mimetypes.guess_type(text.strip(), strict)[0]
    return mimetype or DEFAULT_MIMETYPE


def name(url):
    url = format.url(url)
    up = urllib.parse.urlparse(url)
    name = up.path.split("/")[-1]
    if not name:
        name = up.query.split("=", 1)[::-1][0].split("&", 1)[0]
    if not name:
        name = up.netloc.split(".", 1)[0]
    return name.strip()


# TODO: Recheck in 0.5.x
# def grab_name(url, *args, **kwargs):
# kwargs.setdefault('allow_redirects', True)
# kwargs.setdefault('verify', False)
# r = requests.head(url, *args, **kwargs)
# cd = r.headers.get('content-disposition')
# return url_to_name(cd or url)
