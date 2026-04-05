from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.document_loaders import WebBaseLoader

# Free Search
search_tool = DuckDuckGoSearchRun()

# Free Scraper (Basic)
async def scrape_website(url: str) -> str:
    """Scrapes a URL and returns the text content."""
    loader = WebBaseLoader(url)
    docs = loader.load()
    return docs[0].page_content
