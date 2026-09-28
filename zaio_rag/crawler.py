from collections import deque
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class WebPage:
    url: str
    text: str


def clean_page(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup.select(
        "script, style, noscript, svg, nav, header, footer, aside, form, iframe"
    ):
        element.decompose()
    content = soup.select_one("main, article") or soup.body or soup
    return " ".join(content.stripped_strings)


def _canonical_url(url: str) -> str:
    clean, _fragment = urldefrag(url)
    parsed = urlparse(clean)
    path = parsed.path or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def crawl_zaio(
    start_url: str = "https://www.zaio.io/", max_pages: int = 30, timeout: int = 15
) -> list[WebPage]:
    """Breadth-first crawl public HTML pages on the ZAIO domain."""
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    start_url = _canonical_url(start_url)
    allowed_hosts = {"zaio.io", "www.zaio.io"}
    if urlparse(start_url).hostname not in allowed_hosts:
        raise ValueError("The crawl must start on zaio.io")

    session = requests.Session()
    session.headers.update({"User-Agent": "ZAIO-RAG-Student-Project/1.0"})
    queue = deque([start_url])
    visited = set()
    pages = []

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException:
            continue
        if "text/html" not in response.headers.get("Content-Type", "").lower():
            continue

        text = clean_page(response.text)
        if text:
            pages.append(WebPage(url=url, text=text))

        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.select("a[href]"):
            candidate = _canonical_url(urljoin(url, link["href"]))
            parsed = urlparse(candidate)
            if (
                parsed.scheme in {"http", "https"}
                and parsed.hostname in allowed_hosts
                and candidate not in visited
                and candidate not in queue
            ):
                queue.append(candidate)
    return pages