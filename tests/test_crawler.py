'''Tests for the crawler module.'''

import pathlib
import queue

from dataclasses import dataclass
from typing import Dict
from urllib.robotparser import RobotFileParser

from crawler import crawler, worker

@dataclass
class MockResponse:
    '''Mock HTTP response'''
    status_code: int
    headers: Dict[str, str]
    content: str

@dataclass
class MockArgs:
    '''Mock command line args'''
    start_url: str
    num_workers: int
    timeout: float

def _generate_test_response(status_code: int, content_type: str, content_path: str):
    content_path = pathlib.Path(__file__).parent.resolve().joinpath(content_path)
    with open(content_path, 'r', encoding='UTF-8') as handle:
        content = handle.read()

    return MockResponse(status_code, {'content-type': content_type}, content)

def test_exclude_duplicates(mocker):
    '''Verifies that the crawler only visits each path once and avoids duplicate/circular links'''
    mocker.patch('crawler.crawler.parse_args')
    mock_in_queue = mocker.patch('crawler.crawler.JoinableQueue').return_value
    mock_out_queue = mocker.patch('crawler.crawler.Queue').return_value
    mock_out_queue.get.side_effect = [
        worker.Result(
            'http://example.com',
            False,
            200,
            'text/html',
            [
                'http://example.com',
                'http://example.com/page1',
                'page1',
                'http://example.com/page1/',
                'http://example.com/page1?foo=bar#anchor',
                'page2',
                'http://example.com/page2',
                'http://example.com/page2/'
            ],
            ''
        ),
        queue.Empty()
    ]
    crawler.parse_args.return_value = MockArgs('http://example.com', 0, 0)
    crawler.main()

    assert len(mock_in_queue.put.mock_calls) == 3
    mock_in_queue.put.has_any_call('http://example.com')
    mock_in_queue.put.has_any_call('http://example.com/page1')
    mock_in_queue.put.has_any_call('http://example.com/page2')

def test_same_subdomain_only(mocker):
    '''Verifies that links outside of the starting pages subdomain are excluded from crawling'''
    get = mocker.patch('requests.get')
    get.return_value = _generate_test_response(200, 'text/html', 'data/same_subdomain_only.html')
    result = worker.crawl('http://example.com', 5)
    links = crawler.process_result(result)
    assert links == ['http://example.com/page1']

def test_relative_link_handling(mocker):
    '''Verifies that relative links are converted to absolute URLs on the same subdomain'''
    get = mocker.patch('requests.get')
    get.return_value = _generate_test_response(200, 'text/html', 'data/relative_link_handling.html')
    result = worker.crawl('http://example.com', 5)
    links = crawler.process_result(result)
    assert links == [
        'http://example.com/page1',
        'http://example.com/a/b/c/',
        'http://example.com/foo?bar=baz',
        'http://example.com#anchor'
    ]

def test_meta_nofollow(mocker):
    '''Crawler should respect robots meta-directive and not follow links'''
    get = mocker.patch('requests.get')
    get.return_value = _generate_test_response(200, 'text/html', 'data/meta_robots.html')
    result = worker.crawl('http://example.com', 5)
    links = crawler.process_result(result)
    assert links == []

def test_meta_none(mocker):
    '''Crawler should respect robots meta-directive and not follow links'''
    get = mocker.patch('requests.get')
    get.return_value = _generate_test_response(200, 'text/html', 'data/meta_robots_none.html')
    result = worker.crawl('http://example.com', 5)
    links = crawler.process_result(result)
    assert links == []

def test_robots_txt(mocker):
    '''Crawler should respect robots.txt and not crawl specified paths'''
    mocker.patch('crawler.crawler.parse_args')
    mocker.patch('crawler.crawler.get_robot_parser')
    mock_in_queue = mocker.patch('crawler.crawler.JoinableQueue').return_value
    mock_out_queue = mocker.patch('crawler.crawler.Queue').return_value
    mock_out_queue.get.side_effect = [
        worker.Result(
            'http://example.com',
            False,
            200,
            'text/html',
            [
                '/', # Allowed
                'page1', # Disallowed
                'page1/test', # Disallowed
                'page2', # Allowed
                'page2/test' # Disallowed
            ],
            ''
        ),
        queue.Empty()
    ]
    crawler.parse_args.return_value = MockArgs('http://example.com', 0, 0)

    dummy_parser = RobotFileParser()
    dummy_parser.parse(_generate_test_response(200, 'text/plain', 'data/robots.txt').content.splitlines())
    crawler.get_robot_parser.return_value = dummy_parser
    crawler.main()

    assert len(mock_in_queue.put.mock_calls) == 2
    mock_in_queue.put.has_any_call('http://example.com')
    mock_in_queue.put.has_any_call('http://example.com/page2')