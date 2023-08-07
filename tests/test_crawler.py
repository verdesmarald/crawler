import pathlib
import requests

from dataclasses import dataclass
from typing import Dict

from crawler import crawler

@dataclass
class MockResponse:
    status_code: int
    headers: Dict[str, str]
    content: str

@dataclass
class MockArgs:
    root_domain: str

def _generate_test_response(status_code: int, content_type: str, content_path: str):
    content_path = pathlib.Path(__file__).parent.resolve().joinpath(content_path)
    with open(content_path, 'r') as f:
        content = f.read()
    
    return MockResponse(status_code, {'content-type': content_type}, content)

def test_find_links(mocker):
    '''Verifies that all links are found and relative links are converted to absolute'''
    mocker.patch('requests.get')
    requests.get.return_value = _generate_test_response(200, 'text/html', 'data/test_find_links.html')
    
    links = crawler.crawl('http://example.com')
    assert links == ['http://example.com/page1', 'http://example.com/page2', 'http://example.com/page3']

def test_exclude_duplicates(mocker):
    '''Verifies that the crawler only visits each path once and avoids duplicate/circular links'''
    mocker.patch('crawler.crawler.parse_args')
    mocker.patch('crawler.crawler.crawl')
    crawler.parse_args.return_value = MockArgs('http://example.com')
    crawler.crawl.return_value = [
        'http://example.com',
        'http://example.com/page1',
        'http://example.com/page1',
        'http://example.com/page1/',
        'http://example.com/page2',
        'http://example.com/page2/'
    ]

    crawler.main()

    assert len(crawler.crawl.mock_calls) == 3
    crawler.crawl.assert_any_call('http://example.com')
    crawler.crawl.assert_any_call('http://example.com/page1')
    crawler.crawl.assert_any_call('http://example.com/page2')

def test_same_subdomain_only(mocker):
    '''Verifies that links outside of the starting pages subdomain are excluded from crawling'''
    mocker.patch('requests.get')
    requests.get.return_value = _generate_test_response(200, 'text/html', 'data/test_same_subdomain_only.html')
    
    links = crawler.crawl('http://example.com')
    assert links == ['http://example.com/page1']

def test_non_html_content(mocker):
    '''The crawler should list non-html links but not try to parse their content'''
    mocker.patch('requests.get')

    requests.get.return_value = _generate_test_response(200, 'text/html', 'data/test.html')
    links = crawler.crawl('http://example.com')
    assert links == ['http://example.com/page1']

    for mime in ['application/json', 'image/png', 'video/mpg']:
        requests.get.return_value = _generate_test_response(200, mime, 'data/test.html')
        links = crawler.crawl('http://example.com')
        assert links == []

def test_non_200_response(mocker):
    '''The crawler should correctly report non-200 status codes (e.g. page not found, unauthorized, etc.)'''
    mocker.patch('requests.get')
    
    requests.get.return_value = _generate_test_response(200, 'text/html', 'data/test.html')
    links = crawler.crawl('http://example.com')
    assert links == ['http://example.com/page1']

    for response_code in [400, 401, 404, 500]:
        requests.get.return_value = _generate_test_response(response_code, 'text/html', 'data/test.html')
        links = crawler.crawl('http://example.com')
        assert links == []

