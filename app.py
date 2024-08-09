from flask import Flask, request, jsonify, abort, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import logging
from bs4 import BeautifulSoup
from flask_limiter import Limiter
from flask_caching import Cache
from functools import wraps
from datetime import datetime
from urllib.parse import urlparse
from flask_limiter.util import get_remote_address

from flask_cors import CORS
import re
import whois
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# Remove database configuration
# app.config['SQLALCHEMY_DATABASE_URI'] = 'databases://postgres:postgres@localhost:5432/domains_db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

def get_domain_age(domain):
    try:
        domain_info = whois.whois(domain)
        creation_date = domain_info.creation_date
        
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        
        if not isinstance(creation_date, datetime):
            raise ValueError("Creation date is not a valid datetime object.")
        
        domain_age = (datetime.now() - creation_date).days // 365
        return domain_age
    except Exception as e:
        print(f"Error fetching domain age for {domain}: {e}")
        return None

def calculate_domain_authority(domain):
    try:
        total_backlinks = get_total_backlinks(domain)
        referring_domains = get_referring_domains(domain)
        da = min(100, (total_backlinks + referring_domains) / 2)
        return da
    except Exception as e:
        logging.error(f"Error calculating domain authority for {domain}: {e}")
        return None

def calculate_page_authority(domain):
    try:
        total_backlinks = get_total_backlinks(domain)
        referring_domains = get_referring_domains(domain)
        pa = min(100, (total_backlinks + referring_domains) / 2.5)
        return pa
    except Exception as e:
        logging.error(f"Error calculating page authority for {domain}: {e}")
        return None

def calculate_domain_rating(domain):
    try:
        total_backlinks = get_total_backlinks(domain)
        referring_domains = get_referring_domains(domain)
        dr = min(100, (total_backlinks + referring_domains) / 2.2)
        return dr
    except Exception as e:
        logging.error(f"Error calculating domain rating for {domain}: {e}")
        return None

def calculate_trust_flow(domain):
    try:
        trust_score = get_trust_score(domain)
        tf = min(100, trust_score / 2)
        return tf
    except Exception as e:
        logging.error(f"Error calculating trust flow for {domain}: {e}")
        return None

def calculate_citation_flow(domain):
    try:
        total_backlinks = get_total_backlinks(domain)
        cf = min(100, total_backlinks / 2)
        return cf
    except Exception as e:
        logging.error(f"Error calculating citation flow for {domain}: {e}")
        return None

def calculate_spam_score(domain):
    try:
        spam_score = get_spam_score(domain)
        return min(100, spam_score)
    except Exception as e:
        logging.error(f"Error calculating spam score for {domain}: {e}")
        return None

def get_referring_domains(domain, max_retries=3, timeout=10):
    search_url = f"https://www.google.com/search?q=site:{domain}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(search_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            referring_domains = set()
            for link in soup.find_all('a', href=True):
                href = link['href']
                match = re.search(r'https?://([^/]+)', href)
                if match:
                    referring_domains.add(match.group(1))

            logging.info(f"Found {len(referring_domains)} referring domains.")
            return len(referring_domains)
        except requests.RequestException as e:
            logging.error(f"Request failed: {e}. Retrying... ({attempt + 1}/{max_retries})")
            attempt += 1
            time.sleep(2)

    logging.error("Max retries reached. Could not fetch referring domains.")
    return 0

def get_total_backlinks(domain, max_retries=3, timeout=10):
    search_url = f"https://www.google.com/search?q=site:{domain}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    attempt = 0
    backlinks = set()
    while attempt < max_retries:
        try:
            response = requests.get(search_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all('a', href=True):
                href = link['href']
                match = re.search(r'https?://([^/]+)', href)
                if match:
                    backlink_domain = match.group(1)
                    if backlink_domain != domain:
                        backlinks.add(backlink_domain)

            logging.info(f"Found {len(backlinks)} backlinks.")
            return len(backlinks)
        except requests.RequestException as e:
            logging.error(f"Request failed: {e}. Retrying... ({attempt + 1}/{max_retries})")
            attempt += 1
            time.sleep(2)

    logging.error("Max retries reached. Could not fetch backlinks.")
    return 0

def get_trust_score(domain):
    try:
        total_backlinks = get_total_backlinks(domain)
        referring_domains = get_referring_domains(domain)
        trust_score = min(100, (total_backlinks + referring_domains) / 10)
        return trust_score
    except Exception as e:
        logging.error(f"Error getting trust score for {domain}: {e}")
        return 0

def get_backlink_data(domain):
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
    backlinks, referring_domains = get_backlink_data(domain)

    if referring_domains == 0:
        return 100

    ratio = backlinks / referring_domains

    if ratio > 100:
        spam_score = 100
    elif ratio > 50:
        spam_score = 80
    elif ratio > 20:
        spam_score = 60
    elif ratio > 10:
        spam_score = 40
    else:
        spam_score = 20

    logging.info(f"Calculated spam score for {domain}: {spam_score}")
    return spam_score

# Remove the DomainMetrics model and related functions
# class DomainMetrics(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     domain = db.Column(db.String(255), unique=True, nullable=False, index=True)
#     da = db.Column(db.Float)
#     pa = db.Column(db.Float)
#     dr = db.Column(db.Float)
#     tf = db.Column(db.Float)
#     cf = db.Column(db.Float)
#     spam_score = db.Column(db.Float)
#     rd = db.Column(db.Integer)
#     total_backlinks = db.Column(db.Integer)
#     domain_age = db.Column(db.String(255))
#     trust_score = db.Column(db.Float)

#     def to_dict(self):
#         return {
#             'domain': self.domain,
#             'da': self.da,
#             'pa': self.pa,
#             'dr': self.dr,
#             'tf': self.tf,
#             'cf': self.cf,
#             'spam_score': self.spam_score,
#             'rd': self.rd,
#             'total_backlinks': self.total_backlinks,
#             'domain_age': self.domain_age,
#             'trust_score': self.trust_score
#         }

@app.route('/metrics/<domain>', methods=['GET'])
def get_domain_metrics(domain):
    try:
        parsed_domain = urlparse(domain).netloc
        if not parsed_domain:
            parsed_domain = domain
        
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', parsed_domain):
            return jsonify({'error': 'Invalid domain format.'}), 400

        domain_metrics = cache.get(parsed_domain)
        if domain_metrics:
            logging.info(f"Cache hit for domain: {parsed_domain}")
            return jsonify(domain_metrics)
        else:
            logging.info(f"Cache miss for domain: {parsed_domain}")

        domain_metrics = {
            'domain': parsed_domain,
            'da': calculate_domain_authority(parsed_domain),
            'pa': calculate_page_authority(parsed_domain),
            'dr': calculate_domain_rating(parsed_domain),
            'tf': calculate_trust_flow(parsed_domain),
            'cf': calculate_citation_flow(parsed_domain),
            'spam_score': calculate_spam_score(parsed_domain),
            'rd': get_referring_domains(parsed_domain),
            'total_backlinks': get_total_backlinks(parsed_domain),
            'domain_age': get_domain_age(parsed_domain),
            'trust_score': get_trust_score(parsed_domain)
        }

        cache.set(parsed_domain, domain_metrics, timeout=5 * 60)
        return jsonify(domain_metrics)
    except Exception as e:
        logging.error(f"Error processing domain metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear_cache', methods=['DELETE'])
@limiter.limit("10 per minute")
def clear_cache():
    try:
        cache.clear()
        logging.info("Cache cleared successfully.")
        return jsonify({'message': 'Cache cleared successfully.'}), 200
    except Exception as e:
        logging.error(f"Error clearing cache: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear_cache/<domain>', methods=['DELETE'])
@limiter.limit("10 per minute")
def clear_cache_for_domain(domain):
    try:
        parsed_domain = urlparse(domain).netloc
        if not parsed_domain:
            parsed_domain = domain

        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', parsed_domain):
            return jsonify({'error': 'Invalid domain format.'}), 400

        cache.delete(parsed_domain)
        logging.info(f"Cache cleared for domain: {parsed_domain}")
        return jsonify({'message': f'Cache cleared for domain: {parsed_domain}'}), 200
    except Exception as e:
        logging.error(f"Error clearing cache for domain: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/metrics/<domain>', methods=['POST'])
def update_domain_metrics(domain):
    try:
        parsed_domain = urlparse(domain).netloc
        if not parsed_domain:
            parsed_domain = domain

        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', parsed_domain):
            return jsonify({'error': 'Invalid domain format.'}), 400

        domain_metrics = {
            'domain': parsed_domain,
            'da': calculate_domain_authority(parsed_domain),
            'pa': calculate_page_authority(parsed_domain),
            'dr': calculate_domain_rating(parsed_domain),
            'tf': calculate_trust_flow(parsed_domain),
            'cf': calculate_citation_flow(parsed_domain),
            'spam_score': calculate_spam_score(parsed_domain),
            'rd': get_referring_domains(parsed_domain),
            'total_backlinks': get_total_backlinks(parsed_domain),
            'domain_age': get_domain_age(parsed_domain),
            'trust_score': get_trust_score(parsed_domain)
        }

        cache.set(parsed_domain, domain_metrics, timeout=5 * 60)
        return jsonify(domain_metrics), 200
    except Exception as e:
        logging.error(f"Error updating domain metrics: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
