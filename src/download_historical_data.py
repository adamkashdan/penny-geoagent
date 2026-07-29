"""
Script to download historical MCoRDS L2 Ice Thickness data from NASA NSIDC
using NASA Earthdata credentials (username and password).
"""
from __future__ import annotations
import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_dotenv():
    # Try common locations for .env relative to current working directory
    for path in [".env", "src/.env", "../.env", "penny_agent/.env"]:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip("'\"")


load_dotenv()


class EarthdataSession(requests.Session):
    """Custom session to preserve basic authentication credentials when redirected to Earthdata login."""
    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        if 'Authorization' not in headers:
            if self.auth:
                prepared_request.prepare_auth(self.auth)


def get_granule_links() -> list[tuple[str, str]]:
    """Queries NASA CMR API for all IRMCR2 granules (excluding the current 2017 dataset)."""
    bbox = "-68.3,66.3,-63.7,67.8"
    url = f"https://cmr.earthdata.nasa.gov/search/granules.json?short_name=IRMCR2&bounding_box={bbox}&page_size=500"
    
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        data = response.json()
        granules = data.get('feed', {}).get('entry', [])
        
        targets = []
        for g in granules:
            title = g.get('title')
            # Exclude current 2017 dataset to save bandwidth
            if "2017" in title:
                continue
                
            links = g.get('links', [])
            download_url = None
            for link in links:
                href = link.get('href', '')
                if href.startswith('http') and href.endswith('.csv') and 'nsidc' in href:
                    download_url = href
                    break
            
            if download_url:
                targets.append((title, download_url))
        return targets
    except Exception as e:
        print(f"Error querying NASA CMR API: {e}")
        return []


def download_file(session: EarthdataSession, url: str, filename: str) -> bool:
    """Downloads a file handling Earthdata authentication redirects."""
    dest_path = os.path.join(DATA_DIR, filename)
    print(f"Downloading {filename}...")
    
    try:
        response = session.get(url, stream=True)
        response.raise_for_status()
        
        # Verify content type is indeed binary/data and not HTML login page
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            print(f"  Error: Received HTML login page instead of data for {filename}. Check credentials.")
            return False
            
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  Successfully downloaded to {dest_path}")
        return True
    except Exception as e:
        print(f"  Failed to download {filename}: {e}")
        return False


def main():
    username = os.environ.get("EARTHDATA_USERNAME")
    password = os.environ.get("EARTHDATA_PASSWORD")
    
    if not username or not password:
        print("=== NASA Earthdata Downloader ===")
        print("To download historical MCoRDS L2 datasets (2013, 2014, 2015), please set credentials in .env:")
        print("  EARTHDATA_USERNAME=your_username")
        print("  EARTHDATA_PASSWORD=your_password")
        sys.exit(1)
        
    targets = get_granule_links()
    if not targets:
        print("No historical granules found.")
        sys.exit(0)
        
    print(f"Found {len(targets)} historical files to download.")
    
    session = EarthdataSession()
    session.auth = HTTPBasicAuth(username, password)
    
    success_count = 0
    for filename, url in sorted(targets):
        if download_file(session, url, filename):
            success_count += 1
            
    print(f"\nFinished. Successfully downloaded {success_count}/{len(targets)} files.")


if __name__ == "__main__":
    main()
