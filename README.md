# Crawler

`crawler` is a simple webcrawler that crawls all links on the subdomain of a given starting URL.
* For each page that is crawled, `crawler` will output the visited page URL and a list of links found on the page.
* Links on the same subdomain as the starting URL that have not been seen before will then be crawled and output in the same way.
* Links on a different subdomain or an external domain are still printed, but not followed.
* Links to non-HTML resources such as PDF documents or media files are still printed but not followed.
* `crawler` respects `disallow`/`nofollow` directives from the site `robots.txt` file, as well as `x-robots-tag` or `<meta name="robots">` directives from individual pages.

## Installation
```
pip install crawler
```

## Usage
```
crawler <root_domain> [--num-workers N] [--timeout T]
```
Use `crawler --help` for more information on optional parameters.

## Development

### Installation:
To create an editable install with all required development dependencies, run the following commands:
```
pip install -r requirements-dev.txt
pip install -e .
```
Installing in a python virutal environment for development is strongly recommended.

### Testing:
`crawler` uses the `pytest` framework for unit testing. All tests are located in the `tests/` subdirectory, and can be run with:
```
pytest tests
```

### Linting:
`crawler` follows PEP8 coding style, linting can be performed by running:
```
pylint crawler tests
```