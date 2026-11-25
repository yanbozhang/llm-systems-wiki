"""Bound public HTTPS requests to validated addresses without ambient proxies."""
import http.client
import ipaddress
import re
import socket
import urllib.request
from urllib.parse import urlsplit, urlunsplit


def public_addresses(host, resolver=None):
    addresses = (resolver or socket.getaddrinfo)(host, 443, type=socket.SOCK_STREAM)
    parsed = [ipaddress.ip_address(row[4][0]) for row in addresses]
    if not parsed or any(not address.is_global or address.is_multicast for address in parsed):
        raise ValueError('地址必须解析到公网')
    return addresses


def validate_url(url, resolver=None):
    if not isinstance(url, str) or re.search(r'[\x00-\x20\x7f]', url):
        raise ValueError('地址无效')
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower().rstrip('.')
    if (parsed.scheme != 'https' or parsed.username is not None or parsed.password is not None or not host
            or '%' in host or host == 'localhost' or host.endswith('.localhost')
            or parsed.port not in (None, 443)):
        raise ValueError('仅接受无凭证的公网HTTPS地址')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('地址不接受IP字面量')
    public_addresses(host, resolver)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ''))


def connect_public(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    host, port = address
    if port != 443:
        raise ValueError('仅允许HTTPS默认端口')
    addresses = public_addresses(host)
    last_error = None
    for family, kind, protocol, _, destination in addresses:
        connection = socket.socket(family, kind, protocol)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                connection.settimeout(timeout)
            if source_address:
                connection.bind(source_address)
            connection.connect(destination)
            return connection
        except OSError as exc:
            last_error = exc
            connection.close()
        except BaseException:
            connection.close()
            raise
    raise last_error


class PublicHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        if self._tunnel_host:
            raise ValueError('公开来源抓取不允许代理隧道')
        self._create_connection = connect_public
        super().connect()


class PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request):
        return self.do_open(PublicHTTPSConnection, request, context=self._context)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), PublicHTTPSHandler(), NoRedirect())
