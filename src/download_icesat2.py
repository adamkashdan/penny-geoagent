"""
Script to download selected spring ICESat-2 ATL06 laser altimetry datasets
for the Penny Ice Cap using Earthdata Login credentials.
"""
from __future__ import annotations
import os
import sys
import requests
from requests.auth import HTTPBasicAuth

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ICESAT2_DIR = os.path.join(DATA_DIR, "icesat2")


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


# Selected high-quality spring tracks (April) over Penny Ice Cap (approx 50-90 MB each)
TARGET_GRANULES = [
    (
        "ATL06_20190417104749_02930303_007_01.h5",
        "https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-protected/ATLAS/ATL06/007/2019/04/17/ATL06_20190417104749_02930303_007_01.h5"
    ),
    (
        "ATL06_20210416235755_03541103_007_01.h5",
        "https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-protected/ATLAS/ATL06/007/2021/04/16/ATL06_20210416235755_03541103_007_01.h5"
    ),
    (
        "ATL06_20230415013556_03771905_007_01.h5",
        "https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-protected/ATLAS/ATL06/007/2023/04/15/ATL06_20230415013556_03771905_007_01.h5"
    ),
    (
        "ATL06_20250417021616_04762703_007_01.h5",
        "https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-protected/ATLAS/ATL06/007/2025/04/17/ATL06_20250417021616_04762703_007_01.h5"
    )
]


def download_file(session: EarthdataSession, url: str, filename: str) -> bool:
    """Downloads a file handling Earthdata authentication redirects."""
    dest_path = os.path.join(ICESAT2_DIR, filename)
    
    # Check if file already exists to avoid redundant downloads
    if os.path.exists(dest_path):
        print(f"File {filename} already exists. Skipping download.")
        return True
        
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
        print("=== NASA ICESat-2 Downloader ===")
        print("To download ICESat-2 ATL06 datasets, please set credentials in .env:")
        print("  EARTHDATA_USERNAME=your_username")
        print("  EARTHDATA_PASSWORD=your_password")
        sys.exit(1)
        
    # Create target directory
    os.makedirs(ICESAT2_DIR, exist_ok=True)
    
    print(f"Starting download of {len(TARGET_GRANULES)} selected ICESat-2 spring files...")
    
    session = EarthdataSession()
    session.auth = HTTPBasicAuth(username, password)
    
    success_count = 0
    for filename, url in TARGET_GRANULES:
        if download_file(session, url, filename):
            success_count += 1
            
    print(f"\nFinished. Successfully downloaded {success_count}/{len(TARGET_GRANULES)} files.")


if __name__ == "__main__":
    main()
