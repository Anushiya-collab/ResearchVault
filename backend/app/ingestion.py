import difflib

import httpx
from bs4 import BeautifulSoup


def fetch_url_content(url: str) -> str:
    response = httpx.get(
        url,
        timeout=10.0,
        follow_redirects=True
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    text = soup.get_text(separator=" ", strip=True)

    return text


def generate_text_diff(old_text: str, new_text: str) -> list[str]:
    diff = difflib.ndiff(
        old_text.split(),
        new_text.split()
    )

    return list(diff)