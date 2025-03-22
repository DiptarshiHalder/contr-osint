import json
import requests
import re
from bs4 import BeautifulSoup

def search_snusbase(term: str, search_type: str, cookies=None):
    """Search Snusbase API and return structured JSON."""
    url = "https://snusbase.com/search"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.5",
        "cache-control": "max-age=0",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://snusbase.com",
        "priority": "u=0, i",
        "referer": "https://snusbase.com/search",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "sec-gpc": "1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    
    if cookies is None:
        cookies = {
            "lg": "c5a808c2072e0dda2f4e54b05aceabed191d3b05ebb7e3b17f8adfe03051be8b",
            "rm": "TFJoWDF4dTNRMk1rb0VlODJXWGtTUT09::MahwBb7zELZQKzMiix/3fQ==",
            "a": "nt1gglrc7hp3kh992c47j3qlie"
        }
    
    data = {
        "term": term,
        "searchtype": search_type
    }
    
    response = requests.post(url, headers=headers, cookies=cookies, data=data)
    
    if response.status_code == 200:
        return parse_snusbase_results(response.text)
    else:
        return {"error": f"Request failed with status code {response.status_code}"}

def parse_snusbase_results(html_content):
    """Extract structured results from Snusbase HTML response."""
    if html_content is None:
        return {"error": "No valid HTML content to parse"}
    
    soup = BeautifulSoup(html_content, "html.parser")
    result = {}

    # Extract result count
    result_count_tag = soup.find("span", id="result_count")
    result["result_count"] = int(result_count_tag.text.strip()) if result_count_tag else 0
    
    total_results = {}
    
    content_area = soup.find("div", id="contentArea")
    if content_area:
        for entry in content_area.find_all("div", recursive=False):
            top_bar = entry.find("div", id="topBar")
            if top_bar:
                dataset_name = re.sub(r"\s*View Full\s*$", "", top_bar.text.strip())  
                dataset_info = {}
                
                table = entry.find("table", class_="databaselist")
                if table:
                    for row in table.find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) == 2:
                            key = cells[0].text.strip()
                            value = cells[1].text.strip()
                            dataset_info[key] = value
                
                total_results[dataset_name] = dataset_info
    
    result["total_results"] = total_results
    return result  

if __name__ == "__main__":
    pass