import argparse
import requests

from bs4 import BeautifulSoup
from queue import Queue
from urllib.parse import urljoin, urlparse

from typing import List

def main() -> None:
    parser = argparse.ArgumentParser(description='A simple webcrawler')
    parser.add_argument(
        'root_domain',
        help='The root domain to crawl. This crawler will not crawl links ' \
             'outside this domain, including subdomains.'
    )

    args = parser.parse_args()
    visited = set()
    to_crawl = Queue()
    to_crawl.put(args.root_domain)

    while not to_crawl.empty():
        url = to_crawl.get()
        
        if _get_path(url) in visited:
            continue

        print(f'Crawling {url}')
        next_urls = crawl(url)
        for next_url in next_urls:            
            to_crawl.put(next_url)

        visited.add(_get_path(url))

def crawl(url: str) -> List[str]:
    to_crawl = []

    response = requests.get(url, headers={'user-agent': 'simplecrawler/1.0.0'})
    if response.status_code != 200:
        print(f'\tRequest for: {url} failed with response code {response.status_code}')
        return []
    
    if response.headers['content-type'] != 'text/html':
        print(f'\tRequest for {url} returned non-HTML content of type: {response.headers["content-type"]}')
        return[]
    
    html = BeautifulSoup(response.content, features='html.parser')
    for link in html.find_all('a'):
        link_url = link.get("href")
        absolute_link_url = urljoin(url, link_url)
        print(f'\tFound link: {absolute_link_url}')
        if _get_host(url) == _get_host(absolute_link_url):
            to_crawl.append(absolute_link_url)
        
    return to_crawl

def _get_host(url: str) -> str:
    return urlparse(url).hostname

def _get_path(url: str) -> str:
    path = urlparse(url).path
    if not path.endswith('/'):
        path += '/'
    return path