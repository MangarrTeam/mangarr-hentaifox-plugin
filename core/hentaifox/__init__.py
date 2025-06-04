from plugins.base import MangaPluginBase, Formats, AgeRating, Status, NO_THUMBNAIL_URL
import requests
from lxml import html
import re

import logging
logger = logging.getLogger(__name__)


class HentaiFoxPlugin(MangaPluginBase):
    languages = ["en"]
    base_url = "https://hentaifox.com"

    def search_manga(self, query:str, language:str=None) -> list[dict]:
        logger.debug(f'Searching for "{query}"')
        try:
            words = re.findall(r"[A-z]*", query)
            filtered_words = [w for w in words if len(w) > 0]
            result = " ".join(filtered_words).lower()

            current_page = 1
            of_pages = current_page
            pages_checked = False
            found_mangas = []
            while current_page <= of_pages:
                response = requests.get(f'{self.base_url}/search',
                                            params={
                                                "q": result,
                                                "page": current_page
                                            },
                                            timeout=10
                                            )
                
                response.raise_for_status()

                if not pages_checked:
                    of_pages = self.get_pages_num_from_html(response.content)
                    pages_checked = True

                found_mangas.append(self.get_manga_list_from_html(response.content))
                current_page += 1

            return sum(found_mangas, [])

        except Exception as e:
            logger.error(f'Error while searching manga - {e}')
        return []
    
    def get_pages_num_from_html(self, document) -> int:
        dom = html.fromstring(document)
        pagesNode = dom.xpath("//ul[@class='pagination']/li/a")

        if not pagesNode or len(pagesNode) < 2:
            return 1
        
        return int(pagesNode[-2].text)
    
    def get_manga_list_from_html(self, document) -> list[dict]:
        dom = html.fromstring(document)
        mangaList = dom.xpath("//*[contains(@class, 'lc_galleries')]/*")

        mangas = []
        for mangaItem in mangaList:
            manga_dict = self.search_manga_dict()
            nameNode = mangaItem.xpath(".//h2/a")[0]
            manga_dict["name"] = nameNode.text
            manga_dict["cover"] = mangaItem.xpath(".//a/img")[0].get("data-src")
            manga_dict["url"] = f'{self.base_url}{nameNode.get("href")}'

            mangas.append(manga_dict)

        return mangas

    def get_manga(self, arguments:dict) -> dict:
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            response = requests.get(url,
                                    timeout=10
                                    )
            response.raise_for_status()

            return self.get_manga_from_html(response.content, url)

        except Exception as e:
            logger.error(f'Error while getting manga - {e}')

        return {}
    
    def get_manga_from_html(self, document, url) -> dict:
        dom = html.fromstring(document)
        mangaInfo = dom.xpath("//*[@class='info']")[0]

        manga = self.get_manga_dict()
        manga["name"] = mangaInfo.xpath("./h1")[0].text
        for tagNode in mangaInfo.xpath("./ul[@class='tags']/li/*"):
            manga["tags"].append(tagNode.text.strip())
        manga["url"] = url

        return manga

        
    def get_chapters(self, arguments:dict) -> list[dict]:
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            response = requests.get(url,
                                    timeout=10
                                    )
            response.raise_for_status()

            return self.get_chapters_list_from_html(response.content, arguments, url)

        except Exception as e:
            logger.error(f'Error while getting chapters - {e}')

        return []
        
    def get_chapters_list_from_html(self, document, arguments, url) -> list[dict]:
        dom = html.fromstring(document)
        chapterInfo = dom.xpath("//*[@class='info']")[0]

        chapter = self.get_chapter_dict()
        chapter["name"] = chapterInfo.xpath("./h1")[0].text
        chapter["writer"] = [artistNode.text.strip() for artistNode in chapterInfo.xpath("./ul[@class='artists']/li/*")]
        chapter["age_rating"] = AgeRating.R18_PLUS
        isbn_rex = re.compile(
            r"https:\/\/hentaifox\.com\/gallery\/([0-9]+)\/$"
        )
        match = isbn_rex.match(url)
        chapter["isbn"] = match.group(1)
        chapter["arguments"] = arguments
        chapter["url"] = url
        chapter["source_url"] = chapter["url"]
        

        return [chapter]
    
    def get_pages(self, arguments:dict) -> list[dict]:
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            response = requests.get(url,
                                    timeout=10
                                    )
            response.raise_for_status()

            return self.get_pages_list_from_html(response.content, arguments, url)

        except Exception as e:
            logger.error(f'Error while getting chapters - {e}')

        return []
        
    def get_pages_list_from_html(self, document, arguments, url) -> list[dict]:
        dom = html.fromstring(document)
        pagesNodes = dom.xpath("//*[@class='info']/span[contains(@class, 'pages')]")

        pages = 0
        for pageNode in pagesNodes:
            if pageNode.text.startswith("Pages:"):
                pages = int(pageNode.text.removeprefix("Pages:").strip())
                break
        isbn_rex = re.compile(
            r"https:\/\/hentaifox\.com\/gallery\/([0-9]+)\/$"
        )
        match = isbn_rex.match(url)
        return [{"url": self.get_page_url(f"{self.base_url}/g/{match.group(1)}/{i+1}/"), "arguments": arguments} for i in range(pages)]

    def get_page_url(self, url) -> str:
        response = requests.get(url,
                                timeout=10
                                )
        response.raise_for_status()

        dom = html.fromstring(response.content)
        imageNode = dom.xpath("//*[@class='full_image']//img")[0]

        return imageNode.get("data-src")