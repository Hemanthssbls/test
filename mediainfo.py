import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegraph import Telegraph
import subprocess
import json
from datetime import datetime

# Configuration
BOT_TOKEN = "8551780078:AAE0O2qkX5DYiOVE9u-HNA1XGF3zJkqRy9Y"
TELEGRAPH_TOKEN = "YOUR_TELEGRAPH_TOKEN_HERE"  # Optional: will create new if not provided
DOWNLOAD_DIR = "./downloads"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create download directory
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Initialize Telegraph
telegraph = Telegraph()
try:
    if TELEGRAPH_TOKEN and TELEGRAPH_TOKEN != "YOUR_TELEGRAPH_TOKEN_HERE":
        telegraph.access_token = TELEGRAPH_TOKEN
    else:
        account = telegraph.create_account(short_name='MediaInfoBot')
        TELEGRAPH_TOKEN = account['access_token']
        logger.info(f"Created new Telegraph account. Token: {TELEGRAPH_TOKEN}")
except Exception as e:
    logger.error(f"Telegraph initialization error: {e}")

def format_bytes(bytes_size):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0

def get_mediainfo(file_path):
    """Extract media information using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"FFprobe error: {e}")
        return None

def format_mediainfo(info, filename):
    """Format media info into readable text"""
    if not info:
        return "❌ Could not extract media information"
    
    output = f"📁 <b>File Name:</b> {filename}\n\n"
    
    # Format info
    if 'format' in info:
        fmt = info['format']
        output += f"📊 <b>Format Information:</b>\n"
        output += f"  • Format: {fmt.get('format_long_name', 'N/A')}\n"
        output += f"  • Duration: {float(fmt.get('duration', 0)):.2f} seconds\n"
        output += f"  • Size: {format_bytes(int(fmt.get('size', 0)))}\n"
        output += f"  • Bit Rate: {int(fmt.get('bit_rate', 0)) // 1000} kbps\n\n"
    
    # Streams info
    if 'streams' in info:
        for idx, stream in enumerate(info['streams']):
            codec_type = stream.get('codec_type', 'unknown').upper()
            output += f"🎬 <b>{codec_type} Stream #{idx}:</b>\n"
            output += f"  • Codec: {stream.get('codec_long_name', 'N/A')}\n"
            
            if codec_type == 'VIDEO':
                output += f"  • Resolution: {stream.get('width', 0)}x{stream.get('height', 0)}\n"
                output += f"  • FPS: {eval(stream.get('r_frame_rate', '0/1')):.2f}\n"
                output += f"  • Aspect Ratio: {stream.get('display_aspect_ratio', 'N/A')}\n"
            elif codec_type == 'AUDIO':
                output += f"  • Sample Rate: {stream.get('sample_rate', 'N/A')} Hz\n"
                output += f"  • Channels: {stream.get('channels', 'N/A')}\n"
                output += f"  • Channel Layout: {stream.get('channel_layout', 'N/A')}\n"
            
            if 'bit_rate' in stream:
                output += f"  • Bit Rate: {int(stream['bit_rate']) // 1000} kbps\n"
            output += "\n"
    
    return output

def create_telegraph_page(title, content):
    """Create a Telegraph page with media info"""
    try:
        # Convert HTML tags for Telegraph
        content_html = content.replace('<b>', '<strong>').replace('</b>', '</strong>')
        content_html = content_html.replace('\n', '<br>')
        
        response = telegraph.create_page(
            title=title,
            html_content=content_html,
            author_name='MediaInfo Bot'
        )
        return response['url']
    except Exception as e:
        logger.error(f"Telegraph error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome_text = (
        "👋 <b>Welcome to MediaInfo Bot!</b>\n\n"
        "📤 Send me any video or audio file and I'll extract detailed media information.\n\n"
        "<b>Features:</b>\n"
        "• Video/Audio file analysis\n"
        "• Detailed codec information\n"
        "• Telegraph support for sharing\n"
        "• Format and stream details\n\n"
        "Use /help for more information."
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = (
        "<b>📖 How to use:</b>\n\n"
        "1️⃣ Send a video or audio file\n"
        "2️⃣ Wait for processing (may take a moment)\n"
        "3️⃣ Get detailed media information\n"
        "4️⃣ Optionally share via Telegraph\n\n"
        "<b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "<b>Supported formats:</b>\n"
        "Video: MP4, MKV, AVI, MOV, FLV, etc.\n"
        "Audio: MP3, FLAC, WAV, AAC, OGG, etc."
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle media files"""
    message = update.message
    
    # Get file
    if message.video:
        file = message.video
        file_type = "Video"
    elif message.audio:
        file = message.audio
        file_type = "Audio"
    elif message.document:
        file = message.document
        file_type = "Document"
    else:
        await message.reply_text("❌ Please send a valid media file (video/audio).")
        return
    
    # Check file size (Telegram bot API limit is 20MB for download)
    if file.file_size > 20 * 1024 * 1024:
        await message.reply_text("❌ File is too large. Maximum size: 20MB")
        return
    
    # Send processing message
    status_msg = await message.reply_text("⏳ Processing your file...")
    
    try:
        # Download file
        file_name = getattr(file, 'file_name', f'file_{file.file_id}')
        file_path = os.path.join(DOWNLOAD_DIR, f"{file.file_id}_{file_name}")
        
        await status_msg.edit_text("📥 Downloading file...")
        new_file = await context.bot.get_file(file.file_id)
        await new_file.download_to_drive(file_path)
        
        # Extract media info
        await status_msg.edit_text("🔍 Extracting media information...")
        media_info = get_mediainfo(file_path)
        
        if not media_info:
            await status_msg.edit_text("❌ Could not extract media information. Make sure the file is a valid media file.")
            return
        
        # Format info
        formatted_info = format_mediainfo(media_info, file_name)
        
        # Create inline keyboard
        keyboard = [
            [InlineKeyboardButton("📤 Share via Telegraph", callback_data=f"telegraph_{file.file_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Store info in context for Telegraph callback
        context.user_data[f'info_{file.file_id}'] = {
            'formatted': formatted_info,
            'filename': file_name
        }
        
        # Send result
        await status_msg.delete()
        
        # Split message if too long
        if len(formatted_info) > 4096:
            parts = [formatted_info[i:i+4096] for i in range(0, len(formatted_info), 4096)]
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    await message.reply_text(part, parse_mode='HTML', reply_markup=reply_markup)
                else:
                    await message.reply_text(part, parse_mode='HTML')
        else:
            await message.reply_text(formatted_info, parse_mode='HTML', reply_markup=reply_markup)
        
        # Clean up
        os.remove(file_path)
        
    except Exception as e:
        logger.error(f"Error processing media: {e}")
        await status_msg.edit_text(f"❌ Error processing file: {str(e)}")
        # Clean up on error
        if os.path.exists(file_path):
            os.remove(file_path)

async def telegraph_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Telegraph button callback"""
    query = update.callback_query
    await query.answer()
    
    file_id = query.data.replace('telegraph_', '')
    info_key = f'info_{file_id}'
    
    if info_key not in context.user_data:
        await query.edit_message_text("❌ Information expired. Please send the file again.")
        return
    
    info = context.user_data[info_key]
    
    # Create Telegraph page
    await query.edit_message_reply_markup(reply_markup=None)
    status = await query.message.reply_text("📤 Creating Telegraph page...")
    
    title = f"MediaInfo: {info['filename']}"
    telegraph_url = create_telegraph_page(title, info['formatted'])
    
    if telegraph_url:
        keyboard = [[InlineKeyboardButton("🔗 Open Telegraph Page", url=telegraph_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status.edit_text(
            f"✅ Telegraph page created successfully!\n\n🔗 {telegraph_url}",
            reply_markup=reply_markup
        )
    else:
        await status.edit_text("❌ Failed to create Telegraph page. Please try again.")

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(
        filters.VIDEO | filters.AUDIO | filters.Document.VIDEO | filters.Document.AUDIO,
        handle_media
    ))
    application.add_handler(CallbackQueryHandler(telegraph_callback, pattern='^telegraph_'))
    
    # Start bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
