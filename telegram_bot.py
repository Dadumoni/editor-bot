import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import io
import re
import os
import subprocess
from config import BOT_TOKEN

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a command handler for the start command
def start(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "🎨 Welcome to Thrill Zone Image Editor Bot! 🎨\n\n"
        "I can help you with:\n"
        "✨ Adding watermarks to your images, videos and GIFs\n"
        "🔗 Formatting Terabox links\n\n"
        "Available commands:\n"
        "📝 /help - Show help message\n"
        "🎯 /effects - Show available effects\n\n"
        "Just send me an image, video, GIF or a Terabox link to get started! 🚀"
    )
    update.message.reply_text(welcome_message)

# Define a message handler for images
def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "🤖 Bot Commands:\n\n"
        "🖼 Send an image/video/GIF - I'll add our watermark\n"
        "🔗 Send a Terabox link - I'll format it nicely\n\n"
        "Available Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this message\n"
        "/effects - Show available effects"
    )
    update.message.reply_text(help_text)

def effects_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Available effects:\n- Blur\n- Contour\n- Emboss\n- Sharpen')

def format_terabox_links(text: str) -> str:
    # Define supported Terabox domains
    terabox_domains = ['1024terabox.com', 'terasharelink.com', 'terafileshare.com']
    
    # Find all Terabox links
    links = []
    for line in text.split('\n'):
        for domain in terabox_domains:
            matches = re.finditer(f'https://{domain}/s/[a-zA-Z0-9_-]+', line)
            links.extend([match.group() for match in matches])
    
    # Remove duplicates while preserving order
    unique_links = []
    for link in links:
        if link not in unique_links:
            unique_links.append(link)
    
    if not unique_links:
        return text
    
    # Format the output with clean formatting
    output = "📥 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝 𝐋𝐢𝐧𝐤𝐬/👀𝐖𝐚𝐭𝐜𝐡 𝐎𝐧𝐥𝐢𝐧𝐞\n\n"
    
    for i, link in enumerate(unique_links, 1):
        output += f"Video {i}👇\n{link}\n\n"
    
    output += "Join For More ➥ @Thrill_Zone"
    
    return output.strip()

def text_handler(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text
        formatted_text = format_terabox_links(text)
        if formatted_text != text:
            update.message.reply_text(formatted_text)
        else:
            update.message.reply_text('Please send me an image to edit or a Terabox link to format.')
    except Exception as e:
        logger.error(f'Error processing text: {str(e)}')
        update.message.reply_text('Sorry, there was an error processing your message. Please try again.')


def image_handler(update: Update, context: CallbackContext) -> None:
    try:
        if not update.message.photo:
            update.message.reply_text('Please send me an image to edit.')
            return
            
        photo = update.message.photo[-1]
        photo_file = photo.get_file()
        photo_bytes = photo_file.download_as_bytearray()

        # Open the image
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Add watermark text in center
        draw = ImageDraw.Draw(image)
        text = "Join ➥ @Thrill_Zone"
        font_size = 36
        font = ImageFont.truetype("arial.ttf", font_size)
        
        # Calculate text position for center placement
        text_width = draw.textlength(text, font=font)
        text_height = font_size
        x_pos = (image.width - text_width) // 2
        y_pos = (image.height - text_height) // 2
        
        # Add white background box for better visibility
        padding = 10
        box_coords = [
            x_pos - padding,
            y_pos - padding,
            x_pos + text_width + padding,
            y_pos + text_height + padding
        ]
        draw.rectangle(box_coords, fill='white', outline='white', width=2)
        
        # Draw text in black color
        draw.text((x_pos, y_pos), text, fill='black', font=font)

        # Save and send the edited image with caption
        byte_io = io.BytesIO()
        image.save(byte_io, format='JPEG')
        byte_io.seek(0)

        # Process caption if provided
        if update.message.caption:
            caption = format_terabox_links(update.message.caption)
        else:
            caption = "Join For More ➥ @Thrill_Zone"
        
        update.message.reply_photo(photo=byte_io, caption=caption)
    
    except Exception as e:
        logger.error(f'Error processing image: {str(e)}')
        update.message.reply_text('Sorry, there was an error processing your image. Please try again.')

def video_handler(update: Update, context: CallbackContext) -> None:
    try:
        video = update.message.video or update.message.animation
        if not video:
            update.message.reply_text('Please send me a video or GIF to edit.')
            return

        # Check if FFmpeg is installed
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error('FFmpeg is not installed or not in system PATH')
            update.message.reply_text('Sorry, the video processing service is currently unavailable.')
            return
            
        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        video_file = video.get_file()
        input_path = os.path.join(temp_dir, f'input_{video.file_unique_id}{os.path.splitext(video_file.file_path)[1]}')
        output_path = os.path.join(temp_dir, f'output_{video.file_unique_id}{os.path.splitext(video_file.file_path)[1]}')
        
        # Download video to temp directory
        video_file.download(custom_path=input_path)
        
        # Add watermark text using FFmpeg
        try:
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', "drawtext=text='Join ➥ @Thrill_Zone':fontcolor=black:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=white@0.5",
                '-codec:a', 'copy',
                output_path
            ]
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            
            # Process caption if provided
            if update.message.caption:
                caption = format_terabox_links(update.message.caption)
            else:
                caption = "Join For More ➥ @Thrill_Zone\n\nSearch @Thrill_Zone"
            
            # Send the watermarked video back
            with open(output_path, 'rb') as f:
                if update.message.video:
                    update.message.reply_video(video=f, caption=caption)
                else:
                    update.message.reply_animation(animation=f, caption=caption)
        finally:
            # Clean up temporary files
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
    
    except Exception as e:
        logger.error(f'Error processing video/GIF: {str(e)}')
        update.message.reply_text('Sorry, there was an error processing your video/GIF. Please try again.')

# Define the main function to start the bot
def main() -> None:
    # Create the Updater and pass it your bot's token
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('effects', effects_command))

    # Register the message handlers
    dispatcher.add_handler(MessageHandler(Filters.photo, image_handler))
    dispatcher.add_handler(MessageHandler((Filters.video | Filters.animation), video_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you send a signal to stop
    updater.idle()

if __name__ == '__main__':
    main()