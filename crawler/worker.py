
import logging
import requests
import signal

from bs4 import BeautifulSoup
from dataclasses import dataclass
from multiprocessing import Process, Queue, JoinableQueue
from typing import List

@dataclass
class Result:
    crawled_url: str
    error: bool
    response_status: int
    response_type: str
    links_found: List[str]


def start_worker(id: int, in_queue: JoinableQueue, out_queue: Queue, timeout: float) -> Process:
    worker = Process(
        target=run,
        name=str(id),
        args=(in_queue, out_queue, timeout),
        daemon=True
    )
    worker.start()
    return worker

def run(in_queue: JoinableQueue, out_queue: Queue, timeout: float) -> None:
    # Ignore keyboard interrupt in worker processes
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while True:
        try:
            got_item = False
            url = in_queue.get() # This call blocks until work is available
            got_item = True
            result = crawl(url, timeout)
            out_queue.put(result)
        except Exception as e:
            logging.exception(e)
            result = Result(
                crawled_url=url,
                error=True,
                response_status=0,
                response_type='',
                links_found=[]
            )
            out_queue.put(result)
        finally:
            if got_item:
                in_queue.task_done()

def crawl(url: str, timeout: float) -> Result:
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
        response_type=response.headers['content-type'],
        links_found=[]
    )

    if result.response_status == 200 and 'text/html' in result.response_type:
        html = BeautifulSoup(response.content, features='html.parser')
        result.links_found=[link.get('href') for link in html.find_all('a')]

    return result