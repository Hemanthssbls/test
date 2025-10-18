import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configure your bot token here
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
DOWNLOAD_FOLDER = "downloaded_images"

# Create download folder if it doesn't exist
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when /start command is issued."""
    await update.message.reply_text(
        "🎬 Welcome to BookMyShow Image Downloader Bot!\n\n"
        "Send me a BookMyShow URL and I'll download the images for you.\n\n"
        "Supported commands:\n"
        "/start - Show this message\n"
        "/help - Get help"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when /help command is issued."""
    await update.message.reply_text(
        "📖 How to use this bot:\n\n"
        "1. Copy a BookMyShow movie/event URL\n"
        "2. Send it to this bot\n"
        "3. I'll fetch and send you the images\n\n"
        "Example URL format:\n"
        "https://www.bookmyshow.com/movies/...\n"
        "https://www.bookmyshow.com/events/..."
    )

def fetch_images_from_bms(url: str) -> list:
    """Fetch image URLs from BookMyShow page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find image tags
        image_urls = []
        
        # Look for og:image meta tag (primary image)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_urls.append(og_image['content'])
        
        # Find additional images in the page
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src and ('bookmyshow' in src or src.startswith('http')):
                if src not in image_urls:
                    image_urls.append(src)
        
        return image_urls[:5]  # Limit to 5 images
    
    except Exception as e:
        logger.error(f"Error fetching images: {e}")
        return []

def download_image(img_url: str, filename: str) -> bool:
    """Download image from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(img_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return filepath
    
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle URL sent by user."""
    url = update.message.text.strip()
    
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ Please send a valid URL starting with http:// or https://")
        return
    
    if 'bookmyshow' not in url.lower():
        await update.message.reply_text("❌ Please send a BookMyShow URL")
        return
    
    await update.message.reply_text("⏳ Fetching images from BookMyShow...")
    
    # Fetch images
    image_urls = fetch_images_from_bms(url)
    
    if not image_urls:
        await update.message.reply_text("❌ No images found on this page")
        return
    
    await update.message.reply_text(f"📸 Found {len(image_urls)} image(s). Downloading...")
    
    # Download and send images
    for idx, img_url in enumerate(image_urls):
        try:
            # Generate filename
            filename = f"bookmyshow_{idx + 1}.jpg"
            filepath = download_image(img_url, filename)
            
            if filepath:
                with open(filepath, 'rb') as f:
                    await update.message.reply_photo(photo=f)
                os.remove(filepath)  # Clean up after sending
            
        except Exception as e:
            logger.error(f"Error processing image {idx + 1}: {e}")
            await update.message.reply_text(f"⚠️ Error downloading image {idx + 1}")
    
    await update.message.reply_text("✅ Done! All images have been sent.")

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # Run the bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
