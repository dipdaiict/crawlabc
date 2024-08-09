import requests
from bs4 import BeautifulSoup
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_backlink_data(domain):
    """
    Extracts total backlinks and referring domains for the given domain.
    """
    search_url = f"https://www.google.com/search?q=site:{domain}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        backlinks = set()
        referring_domains = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            match = re.search(r'https?://([^/]+)', href)
            if match:
                backlink_domain = match.group(1)
                if backlink_domain != domain:
                    backlinks.add(href)
                    referring_domains.add(backlink_domain)

        logging.info(f"Found {len(backlinks)} backlinks and {len(referring_domains)} referring domains.")
        return len(backlinks), len(referring_domains)
    except requests.RequestException as e:
        logging.error(f"Error fetching backlink data: {e}")
        return 0, 0

def get_spam_score(domain):
    """
    Calculates the spam score for the given domain based on backlinks and referring domains.
    """
    backlinks, referring_domains = get_backlink_data(domain)

    if referring_domains == 0:
        return 100  # High spam score if no referring domains

    ratio = backlinks / referring_domains

    # Define thresholds for spam score
    if ratio > 100:
        spam_score = 100  # Very high spam score
    elif ratio > 50:
        spam_score = 80   # High spam score
    elif ratio > 20:
        spam_score = 60   # Medium spam score
    elif ratio > 10:
        spam_score = 40   # Low spam score
    else:
        spam_score = 20   # Very low spam score

    logging.info(f"Calculated spam score for {domain}: {spam_score}")
    return spam_score

# Test the function with a sample domain
if __name__ == "__main__":
    domain = "google.com"
    spam_score = get_spam_score(domain)
    print(f"Spam Score for {domain}: {spam_score}")
