"""
Script to download historical MCoRDS L2 Ice Thickness data from NASA NSIDC
using NASA Earthdata credentials (username and password).
"""
from __future__ import annotations
import os
import sys
import json
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


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


def download_file(session: requests.Session, url: str, filename: str, auth: tuple[str, str]) -> bool:
    """Downloads a file handling Earthdata authentication redirects."""
    dest_path = os.path.join(DATA_DIR, filename)
    print(f"Downloading {filename}...")
    
    try:
        # We perform a GET request. The requests library automatically handles redirects.
        # However, to handle Earthdata URS authentication, we use the auth tuple.
        # To avoid sending credentials to non-auth hosts, requests only sends Auth header 
        # on the initial request. If it gets redirected to urs.earthdata.nasa.gov, we must
        # ensure it passes the credentials there.
        # We can do this by using a custom redirect handler or just calling GET directly.
        
        # First attempt: let requests handle basic auth and redirects
        response = session.get(url, auth=auth, stream=True)
        
        # If redirect happens to URS, sometimes auth gets stripped. 
        # We check if the response content is HTML (meaning we ended up on the login page)
        if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
            # Try again by initiating request directly to the login service to get cookies
            login_url = "https://urs.earthdata.nasa.gov/oauth/authorize"
            # We can use the response history to find redirect URL or just do basic request
            print("  Re-authenticating with Earthdata Login...")
            # Trigger login to set session cookies
            session.get(url, auth=auth)
            # Re-download
            response = session.get(url, stream=True)
            
        response.raise_for_status()
        
        # Verify content type is indeed csv/text
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            print(f"  Error: Received HTML login page instead of data for {filename}. Check your credentials.")
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
        print("To download historical MCoRDS L2 datasets (2013, 2014, 2015), please set your credentials:")
        print("  export EARTHDATA_USERNAME=\"your_username\"")
        print("  export EARTHDATA_PASSWORD=\"your_password\"")
        print("\nIf you don't have an account, register for free at: https://urs.earthdata.nasa.gov/")
        sys.exit(1)
        
    targets = get_granule_links()
    if not targets:
        print("No historical granules found.")
        sys.exit(0)
        
    print(f"Found {len(targets)} historical files to download.")
    
    session = requests.Session()
    # Configure session to trust redirects and retain cookies
    auth = (username, password)
    
    success_count = 0
    for filename, url in sorted(targets):
        if download_file(session, url, filename, auth):
            success_count += 1
            
    print(f"\nFinished. Successfully downloaded {success_count}/{len(targets)} files.")


if __name__ == "__main__":
    main()
