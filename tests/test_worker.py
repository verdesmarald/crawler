'''Tests for the worker class'''

import pathlib

from dataclasses import dataclass
from typing import Dict

from crawler import worker

@dataclass
class MockResponse:
    '''Mock HTTP response'''
    status_code: int
    headers: Dict[str, str]
    content: str

def _generate_test_response(status_code: int, content_type: str, content_path: str):
    content_path = pathlib.Path(__file__).parent.resolve().joinpath(content_path)
    with open(content_path, 'r', encoding='UTF-8') as handle:
        content = handle.read()

    return MockResponse(status_code, {'content-type': content_type}, content)

def test_find_links(mocker):
    '''Verifies that all links are found'''
    get = mocker.patch('requests.get')
    get.return_value = _generate_test_response(200, 'text/html', 'data/find_links.html')

    result = worker.crawl('http://example.com', 5)
    assert result.links_found == ['page1', 'http://example.com/page2', 'https://example.net/page3']

def test_non_html_content(mocker):
    '''The crawler should list non-html links but not try to parse their content'''
    get = mocker.patch('requests.get')
    get.return_value = _generate_test_response(200, 'text/html', 'data/test.html')
    result = worker.crawl('http://example.com', 5)
    assert result.links_found == ['page1']

    for mime in ['application/json', 'image/png', 'video/mpg']:
        get.return_value = _generate_test_response(200, mime, 'data/test.html')
        result = worker.crawl('http://example.com', 5)
        assert result.response_status == 200
        assert result.response_type == mime
        assert not result.links_found

def test_non_200_response(mocker):
    '''
    The crawler should correctly report non-200 status codes
    (e.g. page not found, unauthorized, etc.)
    '''
    get = mocker.patch('requests.get')

    get.return_value = _generate_test_response(200, 'text/html', 'data/test.html')
    result = worker.crawl('http://example.com', 5)
    assert result.links_found == ['page1']

    for response_code in [400, 401, 404, 500]:
        get.return_value = _generate_test_response(response_code, 'text/html', 'data/test.html')
        result = worker.crawl('http://example.com', 5)
        assert result.response_status == response_code
        assert result.response_type == 'text/html'
        assert not result.links_found
