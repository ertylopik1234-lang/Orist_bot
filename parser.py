import html
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36"
)

SOCIAL_DOMAINS = {
    "vk.com": "VK",
    "m.vk.com": "VK",
    "t.me": "Telegram",
    "telegram.me": "Telegram",
    "instagram.com": "Instagram",
    "www.instagram.com": "Instagram",
    "youtube.com": "YouTube",
    "www.youtube.com": "YouTube",
    "rutube.ru": "Rutube",
    "ok.ru": "Одноклассники",
    "tiktok.com": "TikTok",
    "www.tiktok.com": "TikTok",
    "linkedin.com": "LinkedIn",
    "www.linkedin.com": "LinkedIn",
    "facebook.com": "Facebook",
    "www.facebook.com": "Facebook",
}


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_url(url):
    if not url:
        return ""

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        return ""

    return url


def get_domain(url):
    try:
        domain = urlparse(url).netloc.lower()
        return domain.removeprefix("www.")
    except Exception:
        return ""


def detect_socials(urls):
    found = []

    for url in urls:
        domain = get_domain(url)

        for social_domain, social_name in SOCIAL_DOMAINS.items():
            if domain == social_domain:
                item = {
                    "name": social_name,
                    "url": url,
                }

                if item not in found:
                    found.append(item)

    return found


def extract_links(soup, base_url):
    links = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()

        if not href:
            continue

        if href.startswith("//"):
            href = "https:" + href

        if not href.startswith(("http://", "https://")):
            continue

        if href not in links:
            links.append(href)

    return links


def extract_emails(text):
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    found = re.findall(pattern, text)

    result = []

    for email in found:
        email = email.lower()

        if email not in result:
            result.append(email)

    return result[:10]


def extract_phones(text):
    patterns = [
        r"\+\d[\d\s().-]{7,}\d",
        r"\b8[\d\s().-]{9,}\d\b",
        r"\b7[\d\s().-]{9,}\d\b",
    ]

    found = []

    for pattern in patterns:
        for value in re.findall(pattern, text):
            value = re.sub(r"\s+", " ", value).strip()

            if value not in found:
                found.append(value)

    return found[:10]


def extract_metadata(soup):
    result = {}

    title = soup.find("title")

    if title:
        result["title"] = clean_text(title.get_text(" ", strip=True))

    description = soup.find(
        "meta",
        attrs={"name": re.compile("^description$", re.I)}
    )

    if description:
        result["description"] = clean_text(
            description.get("content", "")
        )

    og_title = soup.find(
        "meta",
        attrs={"property": "og:title"}
    )

    if og_title:
        result["og_title"] = clean_text(
            og_title.get("content", "")
        )

    og_description = soup.find(
        "meta",
        attrs={"property": "og:description"}
    )

    if og_description:
        result["og_description"] = clean_text(
            og_description.get("content", "")
        )

    return result


def parse_public_page(url, query=""):
    url = normalize_url(url)

    if not url:
        return None

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=12,
            allow_redirects=True,
        )

        if response.status_code >= 400:
            return None

        content_type = response.headers.get(
            "content-type",
            ""
        ).lower()

        if "text/html" not in content_type:
            return None

        final_url = response.url

        soup = BeautifulSoup(
            response.text,
            "lxml"
        )

        for tag in soup(
            ["script", "style", "noscript", "svg"]
        ):
            tag.decompose()

        text = clean_text(
            soup.get_text(" ", strip=True)
        )

        links = extract_links(
            soup,
            final_url
        )

        metadata = extract_metadata(soup)

        socials = detect_socials(
            links
        )

        emails = extract_emails(text)

        phones = extract_phones(text)

        query_match = False

        if query:
            query_clean = clean_text(query).lower()

            query_match = (
                query_clean in text.lower()
                or query_clean in metadata.get(
                    "title",
                    ""
                ).lower()
                or query_clean in metadata.get(
                    "description",
                    ""
                ).lower()
            )

        return {
            "url": final_url,
            "domain": get_domain(final_url),
            "title": metadata.get("title", ""),
            "description": metadata.get(
                "description",
                ""
            ),
            "text": text[:5000],
            "socials": socials,
            "emails": emails,
            "phones": phones,
            "query_match": query_match,
        }

    except Exception as e:
        print("Page parser error:", url, e)
        return None
