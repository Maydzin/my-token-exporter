import os
import logging
from prometheus_client import start_http_server, Gauge
import requests
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.int.e-kama.com")
GROUP_ID = os.getenv("GROUP_ID", "160")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_INTERVAL = 3600

logger.info(f"Configuration loaded - GITLAB_URL: {GITLAB_URL}, GROUP_ID: {GROUP_ID}")
logger.info(f"Access token {'present' if ACCESS_TOKEN else 'not found'}")

token_expires_at = Gauge(
    "gitlab_token_expires_at_seconds",
    "Expiration timestamp of GitLab group access tokens",
    ["token_name", "created_at"]
)

def fetch_tokens():
    headers = {"PRIVATE-TOKEN": ACCESS_TOKEN}
    url = f"{GITLAB_URL}/api/v4/groups/{GROUP_ID}/access_tokens"
    
    try:
        logger.info(f"Making request to GitLab API: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        logger.debug(f"Response status: {response.status_code}")
        
        response.raise_for_status()
        tokens = response.json()
        logger.info(f"Received {len(tokens)} tokens from API")
        
        if not tokens:
            logger.warning("No tokens found in the group")
            
        for token in tokens:
            name = token.get("name", "unnamed-token")
            created_at = token.get("created_at", "unknown")
            expires_at = token.get("expires_at")
            
            if not expires_at:
                logger.debug(f"Skipping token '{name}' - no expiration date")
                continue
                
            try:
                expires_dt = datetime.strptime(expires_at, "%Y-%m-%d")
                expires_ts = int(expires_dt.timestamp())
                logger.info(f"Processing token: {name}, expires at: {expires_at} (timestamp: {expires_ts})")
                
                token_expires_at.labels(
                    token_name=name,
                    created_at=created_at
                ).set(expires_ts)
                
            except ValueError as e:
                logger.error(f"Failed to parse date for token '{name}': {str(e)}")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("Starting GitLab Token Exporter on port 8000")
    start_http_server(8000)
    
    while True:
        logger.debug("Starting new tokens fetch cycle")
        fetch_tokens()
        logger.debug(f"Sleeping for {REFRESH_INTERVAL} seconds")
        time.sleep(REFRESH_INTERVAL)