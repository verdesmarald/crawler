'''
A simple worker process to pull URLs to be crawled from a queue and
perform the actual HTTP requests.
'''
import logging
import signal
from dataclasses import dataclass
from multiprocessing import Process, Queue, JoinableQueue
from typing import List

import requests
from bs4 import BeautifulSoup

@dataclass
class Result:
    '''Results of a single page crawl'''
    crawled_url: str
    error: bool
    response_status: int
    response_type: str
    links_found: List[str]
    meta_robots: str


def start_worker(name: int, in_queue: JoinableQueue, out_queue: Queue, timeout: float) -> Process:
    '''
    Starts a new worker process that consumes URLs to crawl from
    in_queue and publishes crawl results to out_queue.
    '''
    worker = Process(
        target=_run,
        name=str(name),
        args=(in_queue, out_queue, timeout),
        daemon=True
    )
    worker.start()
    return worker

def _run(in_queue: JoinableQueue, out_queue: Queue, timeout: float) -> None:
    # Ignore keyboard interrupt in worker processes
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while True:
        got_item = False
        try:
            url = in_queue.get() # This call blocks until work is available
            got_item = True
            result = crawl(url, timeout)
            out_queue.put(result)
        except Exception as ex: # pylint:disable=broad-exception-caught
            logging.exception(ex)
            result = Result(
                crawled_url=url,
                error=True,
                response_status=0,
                response_type='',
                links_found=[],
                meta_robots=''
            )
            out_queue.put(result)
        finally:
            if got_item:
                in_queue.task_done()

def crawl(url: str, timeout: float) -> Result:
    '''Crawls the specified URL.'''
    response = requests.get(
        url,
        headers={'user-agent': 'simplecrawler/1.0.0'},
        timeout=timeout,
        # Response streaming allows inspection of the response headers before
        # downloading the response body, so we can skip downloading large files
        # and other non-HTML responses.
        stream=True
    )
    result = Result(
        crawled_url=url,
        error=False,
        response_status=response.status_code,
        response_type=response.headers.get('content-type', ''),
        meta_robots=response.headers.get('x-robots-tag', ''),
        links_found=[]
    )

    if result.response_status == 200 and 'text/html' in result.response_type:
        html = BeautifulSoup(response.content, features='html.parser')
        result.links_found=[link.get('href') for link in html.find_all('a')]
        robots = html.find('meta', attrs= {'name': 'robots'})
        if robots:
            result.meta_robots = robots['content']

    return result
