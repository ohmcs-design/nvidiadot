"""
DOT AI - Web Inspector & Multi-Page Crawler
Extracts content, correlates multi-page site architecture, and serves local previews.
Uses BeautifulSoup4 and Trafilatura for fast, reliable DOM & text extraction.
"""
import os
import re
import socket
import logging
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urljoin, urlparse
from typing import Dict, Any, List, Set, Optional
import requests
from bs4 import BeautifulSoup
import trafilatura
import config

logger = logging.getLogger("dot.web_inspector")

class LocalPreviewServer:
    """Lightweight HTTP server to preview workspace HTML/CSS/JS live"""
    def __init__(self, workspace_path: str, port: int = 8765):
        self.workspace_path = workspace_path
        self.port = port
        self.httpd: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False

    def start(self) -> str:
        if self.is_running:
            return f"http://127.0.0.1:{self.port}"

        workspace = self.workspace_path

        class CustomHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=workspace, **kwargs)

            def log_message(self, format, *args):
                pass  # Silence server terminal spam

        # Find available port if 8765 is taken
        for p in range(self.port, self.port + 50):
            try:
                self.httpd = HTTPServer(("127.0.0.1", p), CustomHandler)
                self.port = p
                break
            except OSError:
                continue

        if not self.httpd:
            return ""

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.is_running = True
        return f"http://127.0.0.1:{self.port}"

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.is_running = False


class WebInspector:
    """Multi-page crawler, DOM extractor, and codebase content correlator"""
    def __init__(self):
        self.headers = {
            "User-Agent": "DOT-AI-WebInspector/1.0 (Autonomous Web Analyst; +https://build.nvidia.com)"
        }

    def fetch_single_page(self, url: str) -> Dict[str, Any]:
        """Fetch and extract structured DOM, headings, text, forms, and links from a single page"""
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            html = resp.text

            soup = BeautifulSoup(html, "html.parser")

            title = soup.title.string.strip() if soup.title and soup.title.string else url

            # Headings
            headings = []
            for tag in soup.find_all(["h1", "h2", "h3"]):
                text = tag.get_text().strip()
                if text:
                    headings.append(f"{tag.name.upper()}: {text}")

            # Forms and inputs
            forms = []
            for form in soup.find_all("form"):
                action = form.get("action", "")
                inputs = [inp.get("name", inp.get("type", "input")) for inp in form.find_all(["input", "textarea", "button"])]
                forms.append({"action": action, "inputs": inputs})

            # Clean readable text using trafilatura
            main_text = trafilatura.extract(html) or ""
            if not main_text:
                # Fallback to soup text
                for s in soup(["script", "style", "nav", "footer"]):
                    s.decompose()
                main_text = re.sub(r"\s+", " ", soup.get_text()).strip()

            # Internal and external links
            parsed_base = urlparse(url)
            internal_links = set()
            external_links = set()

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue

                full_url = urljoin(url, href)
                parsed_href = urlparse(full_url)

                if parsed_href.netloc == parsed_base.netloc or not parsed_href.netloc:
                    internal_links.add(full_url)
                else:
                    external_links.add(full_url)

            return {
                "success": True,
                "url": url,
                "title": title,
                "headings": headings[:15],
                "forms": forms[:5],
                "content_snippet": main_text[:2000],
                "internal_links": list(internal_links)[:25],
                "external_links_count": len(external_links)
            }
        except Exception as e:
            return {"success": False, "url": url, "error": str(e)}

    def crawl_website(self, start_url: str, max_pages: int = 4) -> Dict[str, Any]:
        """
        Crawl start_url and explore linked internal pages up to max_pages.
        Produces multi-page site map and content analysis.
        """
        visited: Set[str] = set()
        to_visit: List[str] = [start_url]
        pages_data: List[Dict[str, Any]] = []

        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc

        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue

            visited.add(current_url)
            page_info = self.fetch_single_page(current_url)

            if page_info["success"]:
                pages_data.append(page_info)
                # Queue unvisited internal links
                for link in page_info.get("internal_links", []):
                    if link not in visited and link not in to_visit:
                        to_visit.append(link)
            else:
                pages_data.append({"url": current_url, "error": page_info.get("error", "Failed")})

        # Summary of site structure
        summary = {
            "start_url": start_url,
            "domain": base_domain,
            "total_pages_analyzed": len(pages_data),
            "site_tree": [
                {
                    "url": p.get("url"),
                    "title": p.get("title", "Error"),
                    "headings": p.get("headings", []),
                    "links_found": len(p.get("internal_links", []))
                }
                for p in pages_data if "title" in p
            ],
            "pages": pages_data
        }

        return summary
