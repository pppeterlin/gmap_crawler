from bs4 import BeautifulSoup

def extract_info(html):
    """ Extract store info from html
    """
    
    soup = BeautifulSoup(html, "html.parser")
    stores = []
    for div in soup.select("div.Nv2PK"):
        title = div.select_one(".hfpxzc[aria-label]")
        rating = div.select_one(".ZkP5Je[aria-label]")
        url = div.select_one(".hfpxzc[href]")

        stores.append({
            "title": title["aria-label"] if title else "N/A",
            "rating": rating["aria-label"] if rating else "N/A",
            "url": url["href"] if url else "N/A"
        })

    return stores

