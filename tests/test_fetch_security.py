import io
import socket
import ssl
import unittest
import urllib.request
from unittest.mock import Mock, patch

from scripts import public_http
from scripts import wiki_tool as wiki


class FeedNetworkBoundaryTests(unittest.TestCase):
    def test_private_dns_is_rejected_before_opening_feed(self):
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 443))]
        opener = Mock()
        opener.open.return_value = io.BytesIO(b'<rss/>')
        with patch('socket.getaddrinfo', return_value=addresses), \
                patch('urllib.request.build_opener', return_value=opener):
            with self.assertRaises(ValueError):
                wiki.fetch_feed('https://feeds.example.org/feed')
        opener.open.assert_not_called()

    def test_invalid_authorities_are_rejected_before_opening_feed(self):
        for url in ('https://@example.org/feed', 'https://example.org:8443/feed',
                    'https://exam\tple.org/feed'):
            with self.subTest(url=url):
                opener = Mock()
                opener.open.return_value = io.BytesIO(b'<rss/>')
                with patch('urllib.request.build_opener', return_value=opener):
                    with self.assertRaises(ValueError):
                        wiki.fetch_feed(url)
                opener.open.assert_not_called()


def addresses(*ips):
    return [(socket.AF_INET6 if ':' in address else socket.AF_INET, socket.SOCK_STREAM, 6, '',
             (address, 443, 0, 0) if ':' in address else (address, 443)) for address in ips]


class PublicConnectionTests(unittest.TestCase):
    def test_dns_rebinding_is_rejected_at_connection_time(self):
        with patch('socket.getaddrinfo', side_effect=[addresses('8.8.8.8'), addresses('127.0.0.1')]), \
                patch('socket.socket') as create_socket:
            public_http.validate_url('https://papers.example.org/article')
            with self.assertRaises(ValueError):
                public_http.PublicHTTPSConnection('papers.example.org').connect()
        create_socket.assert_not_called()

    def test_socket_uses_checked_address_without_resolving_hostname_again(self):
        with patch('socket.getaddrinfo', return_value=addresses('8.8.8.8')) as resolver, \
                patch('socket.socket') as create_socket:
            connected = public_http.connect_public(('papers.example.org', 443), 20)
        resolver.assert_called_once_with('papers.example.org', 443, type=socket.SOCK_STREAM)
        create_socket.return_value.connect.assert_called_once_with(('8.8.8.8', 443))
        create_socket.return_value.settimeout.assert_called_once_with(20)
        self.assertIs(connected, create_socket.return_value)

    def test_non_public_empty_or_mixed_answers_never_open_socket(self):
        for answer in (addresses('::1'), addresses('169.254.169.254'),
                       addresses('8.8.8.8', '10.0.0.1'), addresses('224.0.0.1'), []):
            with self.subTest(answer=answer), patch('socket.getaddrinfo', return_value=answer), \
                    patch('socket.socket') as create_socket:
                with self.assertRaises(ValueError):
                    public_http.connect_public(('papers.example.org', 443), 20)
                create_socket.assert_not_called()

    def test_ipv6_socket_preserves_full_address(self):
        answer = addresses('2606:4700:4700::1111')
        with patch('socket.getaddrinfo', return_value=answer), patch('socket.socket') as create_socket:
            public_http.connect_public(('papers.example.org', 443), 20)
        create_socket.assert_called_once_with(socket.AF_INET6, socket.SOCK_STREAM, 6)
        create_socket.return_value.connect.assert_called_once_with(answer[0][4])

    def test_failed_socket_is_closed_before_next_public_address(self):
        failed, succeeded = Mock(), Mock()
        failed.connect.side_effect = OSError('unreachable')
        with patch('socket.getaddrinfo', return_value=addresses('8.8.8.8', '1.1.1.1')), \
                patch('socket.socket', side_effect=[failed, succeeded]):
            connected = public_http.connect_public(('papers.example.org', 443), 20)
        failed.close.assert_called_once()
        succeeded.connect.assert_called_once_with(('1.1.1.1', 443))
        self.assertIs(connected, succeeded)

    def test_all_failed_sockets_are_closed_and_failure_propagates(self):
        connection = Mock()
        failure = OSError('unreachable')
        connection.connect.side_effect = failure
        with patch('socket.getaddrinfo', return_value=addresses('8.8.8.8')), \
                patch('socket.socket', return_value=connection):
            with self.assertRaises(OSError) as raised:
                public_http.connect_public(('papers.example.org', 443), 20)
        self.assertIs(raised.exception, failure)
        connection.close.assert_called_once()

    def test_interrupted_socket_is_closed(self):
        connection = Mock()
        connection.connect.side_effect = KeyboardInterrupt
        with patch('socket.getaddrinfo', return_value=addresses('8.8.8.8')), \
                patch('socket.socket', return_value=connection):
            with self.assertRaises(KeyboardInterrupt):
                public_http.connect_public(('papers.example.org', 443), 20)
        connection.close.assert_called_once()

    def test_tls_keeps_original_hostname_for_certificate_and_sni(self):
        context = Mock(spec=ssl.SSLContext)
        connection = public_http.PublicHTTPSConnection('papers.example.org', context=context, timeout=20)
        with patch.object(public_http, 'connect_public', return_value=Mock()) as connect:
            connection.connect()
        context.wrap_socket.assert_called_once_with(connect.return_value, server_hostname='papers.example.org')
        self.assertIs(connection.sock, context.wrap_socket.return_value)
        connection.close()

    def test_proxy_tunnels_are_rejected_before_connecting(self):
        connection = public_http.PublicHTTPSConnection('proxy.example.org')
        connection.set_tunnel('papers.example.org', 443)
        with patch.object(public_http, 'connect_public') as connect:
            with self.assertRaises(ValueError):
                connection.connect()
        connect.assert_not_called()

    def test_non_https_port_is_rejected_before_dns(self):
        with patch('socket.getaddrinfo') as resolver:
            with self.assertRaises(ValueError):
                public_http.connect_public(('papers.example.org', 8443), 20)
        resolver.assert_not_called()

    def test_opener_disables_ambient_proxies_and_automatic_redirects(self):
        with patch('urllib.request.build_opener') as factory:
            public_http.public_opener()
        handlers = factory.call_args.args
        self.assertEqual(next(handler.proxies for handler in handlers
                              if isinstance(handler, urllib.request.ProxyHandler)), {})
        self.assertTrue(any(isinstance(handler, public_http.PublicHTTPSHandler) for handler in handlers))
        self.assertTrue(any(isinstance(handler, public_http.NoRedirect) for handler in handlers))

    def test_handler_uses_public_connection(self):
        handler = public_http.PublicHTTPSHandler()
        request = urllib.request.Request('https://papers.example.org/article')
        with patch.object(handler, 'do_open') as open_connection:
            handler.https_open(request)
        open_connection.assert_called_once_with(public_http.PublicHTTPSConnection, request, context=handler._context)
