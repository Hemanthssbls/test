import requests
from bs4 import BeautifulSoup
import re
import time
from telegram import Bot
from telegram.error import TelegramError
import asyncio
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MagnetLinkPoster:
    def __init__(self, bot_token, channel_id):
        """
        Initialize the magnet link poster
        
        Args:
            bot_token (str): Your Telegram bot token from @BotFather
            channel_id (str): Your channel ID (e.g., '@yourchannel' or '-100xxxxxxxxxx')
        """
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.bot = Bot(token=bot_token)
        self.posted_magnets = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_page(self, url, retries=3):
        """Fetch webpage with retry logic"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(5)
                else:
                    return None
    
    def extract_magnet_links(self, html_content, base_url):
        """Extract all magnet links from HTML content"""
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        magnet_links = []
        
        # Find all anchor tags with magnet links
        for link in soup.find_all('a', href=re.compile(r'^magnet:\?')):
            magnet_url = link.get('href')
            
            # Extract movie title from surrounding context
            title = None
            parent = link.find_parent(['div', 'article', 'section'])
            if parent:
                title_elem = parent.find(['h1', 'h2', 'h3', 'h4'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            if not title:
                title = link.get_text(strip=True) or "Movie Link"
            
            magnet_links.append({
                'magnet': magnet_url,
                'title': title
            })
        
        # Also check for onclick events or data attributes
        for elem in soup.find_all(attrs={'data-magnet': True}):
            magnet_url = elem.get('data-magnet')
            title = elem.get_text(strip=True) or "Movie Link"
            magnet_links.append({
                'magnet': magnet_url,
                'title': title
            })
        
        return magnet_links
    
    async def post_to_telegram(self, magnet_data):
        """Post magnet link to Telegram channel"""
        try:
            # Format message
            message = f"🎬 **{magnet_data['title']}**\n\n"
            message += f"🧲 Magnet Link:\n`{magnet_data['magnet']}`"
            
            # Send message
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            logger.info(f"Posted: {magnet_data['title']}")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    async def process_url(self, url):
        """Process a single URL and post new magnet links"""
        logger.info(f"Fetching: {url}")
        html_content = self.fetch_page(url)
        
        if not html_content:
            logger.error("Failed to fetch page")
            return 0
        
        magnet_links = self.extract_magnet_links(html_content, url)
        logger.info(f"Found {len(magnet_links)} magnet links")
        
        posted_count = 0
        for magnet_data in magnet_links:
            magnet_hash = magnet_data['magnet'][:100]  # Use first 100 chars as hash
            
            if magnet_hash not in self.posted_magnets:
                success = await self.post_to_telegram(magnet_data)
                if success:
                    self.posted_magnets.add(magnet_hash)
                    posted_count += 1
                    await asyncio.sleep(2)  # Rate limiting
        
        return posted_count
    
    async def run(self, target_url, interval=300):
        """
        Run the bot continuously
        
        Args:
            target_url (str): URL to monitor
            interval (int): Check interval in seconds (default: 300 = 5 minutes)
        """
        logger.info("Starting Magnet Link Poster Bot...")
        
        while True:
            try:
                posted = await self.process_url(target_url)
                logger.info(f"Posted {posted} new magnet links")
                logger.info(f"Waiting {interval} seconds before next check...")
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(60)


async def main():
    # Configuration
    BOT_TOKEN = "7957179402:AAHKZI8C8YhZ3zVf74MDQMh4ACudYIRWS20"  # Get from @BotFather
    CHANNEL_ID = "-1002597997676"  # Your channel username or ID
    TARGET_URL = "https://www.5movierulz.tienda/"
    CHECK_INTERVAL = 300  # 5 minutes
    
    # Initialize and run
    poster = MagnetLinkPoster(BOT_TOKEN, CHANNEL_ID)
    await poster.run(TARGET_URL, CHECK_INTERVAL)


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
