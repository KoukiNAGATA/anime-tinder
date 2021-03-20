import json
import os

from bs4 import BeautifulSoup
import requests
from logzero import logger

DOWNLOAD_PATH = "./download"


def main() -> None:
    if not os.path.isdir(DOWNLOAD_PATH):
        os.mkdir(DOWNLOAD_PATH)

    anime_link_per_age = "https://ja.wikipedia.org/wiki/Category:%E5%90%84%E5%B9%B4%E3%81%AE%E3%83%86%E3%83%AC%E3%83%93%E3%82%A2%E3%83%8B%E3%83%A1"

    try:
        with open(os.path.join(DOWNLOAD_PATH, "anime_link_per_age.html")) as fp:
            text = fp.read()
    except FileNotFoundError:
        r = requests.get(anime_link_per_age)
        text = r.text
        with open(os.path.join(DOWNLOAD_PATH, "anime_link_per_age.html"), "w") as fp:
            fp.write(r.text)

    soup = BeautifulSoup(text, "html.parser")
    link_area = soup.select_one("#mw-subcategories")
    links = link_area.find_all("a")

    url_base = "https://ja.wikipedia.org/"

    animeinfo = dict()
    count = 0
    for a in links:
        url = url_base + a.attrs["href"]
        text = a.text
        year = text[:4]

        try:
            with open(os.path.join(DOWNLOAD_PATH, f"anime_{year}.html")) as fp:
                text = fp.read()
        except FileNotFoundError:
            logger.warning(
                f"Downloading from {url}. This operation can overwhelm the server"
            )
            r = requests.get(url)
            text = r.text
            with open(os.path.join(DOWNLOAD_PATH, f"anime_{year}.html"), "w") as fp:
                fp.write(r.text)

        soup = BeautifulSoup(text, "html.parser")
        link_area = soup.select_one("#mw-pages")
        links_in_the_year = link_area.find_all("a")

        for anime in links_in_the_year:
            href = anime.attrs["href"]
            title = anime.text
            animeinfo[str(count)] = dict()
            animeinfo[str(count)]["title"] = title
            animeinfo[str(count)]["url"] = url_base + href
            animeinfo[str(count)]["year"] = year

            logger.info(f"{title} collected!")
            count += 1

    filename = "animeinfo.json"
    with open(filename, "w") as fp:

        logger.info(f"...creating {filename}")
        json.dump(animeinfo, fp, ensure_ascii=False)


if __name__ == "__main__":
    main()
