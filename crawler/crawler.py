'''
This is a simple webcrawler. Starting from the specified start_page, it will
find and print all links, then continue crawling any linked pages that are
on the same subdomain as the start_page.

Links to other domains or subdomains, and links to non-HTML resources are
printed but not followed by this tool.
'''

import argparse
import logging
import time
import queue

from multiprocessing import Queue, JoinableQueue
from typing import List
from urllib.parse import urljoin, urlparse

from crawler import worker

def main() -> None:
    '''
    Entry point for the crawler
    
    This function sets up the worker processes, queues URLs to be crawled,
    and processes crawl results, avoiding duplicate page vists.
    '''
    logging.basicConfig(level=logging.INFO)
    in_queue = JoinableQueue()
    out_queue = Queue()
    seen = set()

    args = parse_args()

    in_queue.put(args.start_url)
    seen.add(get_path(args.start_url))

    _workers = [
        worker.start_worker(i, in_queue, out_queue, args.timeout)
        for i in range(args.num_workers)
    ]
    print(f'Started {args.num_workers} workers')
    while True:
        try:
            # Block waiting for a result from any worker
            result: worker.Result = out_queue.get(timeout=args.timeout)
            for link in process_result(result):
                if get_path(link) not in seen:
                    seen.add(get_path(link))
                    in_queue.put(link)
        except queue.Empty:
            if not in_queue.empty():
                # Wait a little longer if the in_queue is not empty,
                # if there are still no results after that something has gone wrong
                time.sleep(2*args.timeout)
                if out_queue.empty():
                    print('Processing is hung, exiting')
                    break
            else:
                # Wait for any remaining in-progress tasks to complete,
                # then exit if the out_queue is still empty
                in_queue.join()
                if out_queue.empty():
                    break
        except KeyboardInterrupt:
            break
        except Exception as ex: #pylint:disable=broad-exception-caught
            logging.exception(ex)

    if not in_queue.empty():
        print('Emptying work queue')
        while not in_queue.empty():
            in_queue.get()
            in_queue.task_done()
        in_queue.join()

    print(f'Crawled {len(seen)} distinct pages')
    print('Done!')

def parse_args() -> argparse.Namespace:
    '''Parses comand-line arguments to the crawler'''
    parser = argparse.ArgumentParser(description = 'A simple webcrawler')
    parser.add_argument(
        'start_url',
        help = 'The root domain to crawl. This crawler will not crawl links ' \
             'outside this domain, including subdomains.'
    )
    parser.add_argument(
        '-n', '--num-workers',
        type=int,
        default=1,
        help='Number of worker processes to use.'
    )
    parser.add_argument(
        '-t', '--timeout',
        type=float,
        default=2,
        help='Timeout (in seconds) when requesting each page.'
    )
    return parser.parse_args()

def process_result(result: worker.Result) -> List[str]:
    '''
    Processes the results of a single page crawl.
    
    This includes outputting the links that were found, logging failed
    requests and non-HTML resources, and converting all relative URLs
    to absolute URLs.
    '''
    print(f'Crawled {result.crawled_url}')

    if result.error:
        logging.error(f'Error requesting: {result.crawled_url}')
        return []

    if result.response_status != 200:
        logging.error(f'Request for: {result.crawled_url} failed with '\
                      'response code {result.response_status}')
        return []

    if not 'text/html' in result.response_type:
        logging.info(f'Request for {result.crawled_url} returned non-HTML '\
                     'content of type: {result.response_type}')
        return []

    follow_host = get_host(result.crawled_url)
    to_crawl = []
    for link in result.links_found:
        # Convert from relative to absolute url if needed
        link_url = urljoin(result.crawled_url, link)
        #print(f'\tFound link: {link_url}')
        if get_host(link_url) == follow_host:
            to_crawl.append(link_url)

    return to_crawl

def get_host(url: str) -> str:
    '''
    Gets the hostname component from a URL
    
    e.g. given https://example.com/some/path?query#anchor,
    returns example.com
    '''
    return urlparse(url).hostname

def get_path(url: str) -> str:
    '''
    Gets the path component from a URL, adding a trailing / if missing

    e.g. given https://example.com/some/path?query#anchor,
    returns some/path/
    '''
    path = urlparse(url).path
    if not path.endswith('/'):
        path += '/'
    return path

if __name__ == '__main__':
    main()
