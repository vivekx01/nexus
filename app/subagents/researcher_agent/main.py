from .tools import search_tool, scrape_website

researcher_subagent = {
    "name": "deep_researcher",
    "description": (
        "Searches the web for any information — current events, news, recent facts, "
        "prices, people, companies, how-to guides, or deep research with citations. "
        "Use this whenever the answer might have changed since the model's training cutoff, "
        "or when the user asks to search, look up, find, or check something online."
    ),
    "system_prompt": """You are a Lead Researcher. 
    1. Start by breaking the user's query into 2-3 search terms.
    2. Use DuckDuckGo to find relevant URLs.
    3. Scrape the most promising URLs to get deep details.
    4. If the info is missing, try a different search query.
    5. Summarize everything into a clean report for the manager.""",
    "tools": [search_tool, scrape_website]
}
