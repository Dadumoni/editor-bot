import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import io
import re
import os
from config import BOT_TOKEN
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple
from queue import Queue
import threading
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running!'

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    server = Thread(target=run_flask)
    server.start()
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a command handler for the start command
def start(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "🎨 Welcome to Thrill Zone Image Editor Bot!\n\n"
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
    terabox_domains = ['1024terabox.com', 'terasharelink.com', 'terafileshare.com', 'terabox.com', 'teraboxlink.com']
    
    # Find all Terabox links using a more flexible pattern
    links = []
    pattern = r'https?://(?:www\.)?(?:' + '|'.join(map(re.escape, terabox_domains)) + r')/s/[a-zA-Z0-9_-]+'
    matches = re.finditer(pattern, text, re.IGNORECASE)
    links = [match.group() for match in matches]
    
    # Remove duplicates while preserving order
    unique_links = []
    for link in links:
        if link not in unique_links:
            unique_links.append(link)
    
    if not unique_links:
        return "Join For More ➥ @Thrill_Zone"
    
    # Format the output with clean formatting and proper spacing
    output = "📥 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝 𝐋𝐢𝐧𝐤𝐬/👀𝐖𝐚𝐭𝐜𝐡 𝐎𝐧𝐥𝐢𝐧𝐞\n\n"
    
    for i, link in enumerate(unique_links, 1):
        output += f"𝐕𝐢𝐝𝐞𝐨 {i}.⚡️\n {link}\n\n"
    
    output += "Join For More ➥ @Thrill_Zone"
    return output
    
    return output

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


def process_single_image(photo_data: Tuple[bytes, str]) -> Tuple[bytes, str]:
    photo_bytes, caption = photo_data
    try:
        # Open the image
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Add watermark text in center
        draw = ImageDraw.Draw(image)
        text = "Join - @Thrill_Zone"
        font_size = min(36, image.width // 20)  # Adjust font size based on image width
        font = ImageFont.truetype("arial.ttf", font_size)
        
        # Calculate text position for center placement
        text_width = draw.textlength(text, font=font)
        text_height = font_size
        x_pos = (image.width - text_width) // 2
        y_pos = (image.height - text_height) // 2
        
        # Add semi-transparent white background box for better visibility
        padding = font_size // 3
        box_coords = [
            x_pos - padding,
            y_pos - padding,
            x_pos + text_width + padding,
            y_pos + text_height + padding
        ]
        # Create semi-transparent background
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(box_coords, fill=(255, 255, 255, 180))
        
        # Convert image to RGBA if it isn't already
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Composite the overlay onto the image
        image = Image.alpha_composite(image, overlay)
        
        # Draw text in black color
        draw = ImageDraw.Draw(image)
        draw.text((x_pos, y_pos), text, fill=(0, 0, 0, 255), font=font)

        # Save the edited image
        byte_io = io.BytesIO()
        image = image.convert('RGB')  # Convert back to RGB for JPEG format
        image.save(byte_io, format='JPEG', quality=95)
        byte_io.seek(0)
        
        return byte_io.getvalue(), caption
    except Exception as e:
        logger.error(f'Error processing image: {str(e)}')
        return None, None

def image_handler(update: Update, context: CallbackContext) -> None:
    try:
        if not update.message.photo:
            update.message.reply_text('Please send me an image to edit.')
            return
            
        # Get the original photo from the message
        photo = update.message.photo[-1]  # Get the highest resolution photo
        photo_file = photo.get_file()
        photo_bytes = photo_file.download_as_bytearray()
        caption = format_terabox_links(update.message.caption) if update.message.caption else "Join For More ➥ @Thrill_Zone"
        
        # Process the image
        processed_image, caption = process_single_image((photo_bytes, caption))
        
        # Send the processed image
        if processed_image:
            update.message.reply_photo(photo=processed_image, caption=caption)
    
    except Exception as e:
        logger.error(f'Error processing image: {str(e)}')
        update.message.reply_text('Sorry, there was an error processing your image. Please try again.')

def process_single_video(video_data: Tuple[bytes, str, bool]) -> Tuple[bytes, str]:
    video_bytes, caption, is_animation = video_data
    try:
        # Create unique temporary files for this thread
        thread_id = threading.get_ident()
        input_path = f'temp_input_{thread_id}.mp4'
        output_path = f'temp_output_{thread_id}.mp4'
        
        with open(input_path, 'wb') as f:
            f.write(video_bytes)
        
        # Load the video using moviepy
        video = VideoFileClip(input_path)
        
        # Create watermark text
        watermark_text = "Join - @Thrill_Zone"
        fontsize = int(min(video.w, video.h) / 20)
        
        # Create text clip with white background
        txt_clip = TextClip(watermark_text, fontsize=fontsize, color='black', bg_color='white', 
                           font='Arial', stroke_color='white', stroke_width=2)
        txt_clip = txt_clip.set_opacity(0.7)  # Make it semi-transparent
        txt_clip = txt_clip.set_position('center')
        txt_clip = txt_clip.set_duration(video.duration)
        
        # Overlay the text on the video
        final_clip = CompositeVideoClip([video, txt_clip])
        
        # Write the result to a file
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
        
        # Clean up moviepy clips
        video.close()
        final_clip.close()
        
        # Read the processed video
        with open(output_path, 'rb') as f:
            processed_video = f.read()
        
        # Clean up temporary files
        os.remove(input_path)
        os.remove(output_path)
        
        return processed_video, caption
    except Exception as e:
        logger.error(f'Error processing video: {str(e)}')
        # Clean up temporary files in case of error
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        return None, None

def video_handler(update: Update, context: CallbackContext) -> None:
    try:
        videos = []
        if update.message.video:
            videos.append((update.message.video, False))
        elif update.message.animation:
            videos.append((update.message.animation, True))
            
        if not videos:
            update.message.reply_text('Please send me a video or GIF to edit.')
            return

        # Process up to 100 videos concurrently
        video_data = []
        for video, is_animation in videos[:100]:
            video_file = video.get_file()
            video_bytes = video_file.download_as_bytearray()
            caption = format_terabox_links(update.message.caption) if update.message.caption else "Join For More ➥ @Thrill_Zone"
            video_data.append((video_bytes, caption, is_animation))

        # Process videos concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(5, len(video_data))) as executor:
            results = list(executor.map(process_single_video, video_data))

        # Send processed videos
        for processed_video, caption in results:
            if processed_video:
                if is_animation:
                    update.message.reply_animation(animation=processed_video, caption=caption)
                else:
                    update.message.reply_video(video=processed_video, caption=caption)
    
    except Exception as e:
        logger.error(f'Error processing video/GIF: {str(e)}')
        update.message.reply_text('Sorry, there was an error processing your video/GIF. Please try again.')
        # Clean up temporary files in case of error
        if os.path.exists('temp_input.mp4'):
            os.remove('temp_input.mp4')
        if os.path.exists('temp_output.mp4'):
            os.remove('temp_output.mp4')


# Define the main function to start the bot
def channel_post_handler(update: Update, context: CallbackContext) -> None:
    try:
        # Handle photos
        if update.message.photo:
            photo = update.message.photo[-1]
            photo_file = photo.get_file()
            photo_bytes = photo_file.download_as_bytearray()
            processed_image, caption = process_single_image((photo_bytes, update.message.caption or "Join For More ➥ @Thrill_Zone"))
            if processed_image:
                context.bot.send_photo(chat_id=update.message.chat_id, photo=processed_image, caption=caption)
        
        # Handle videos and animations
        elif update.message.video or update.message.animation:
            video = update.message.video or update.message.animation
            video_file = video.get_file()
            video_bytes = video_file.download_as_bytearray()
            processed_video, caption = process_single_video((video_bytes, update.message.caption or "Join For More ➥ @Thrill_Zone", bool(update.message.animation)))
            if processed_video:
                if update.message.animation:
                    context.bot.send_animation(chat_id=update.message.chat_id, animation=processed_video, caption=caption)
                else:
                    context.bot.send_video(chat_id=update.message.chat_id, video=processed_video, caption=caption)
        
        # Handle text messages (Terabox links)
        elif update.message.text:
            formatted_text = format_terabox_links(update.message.text)
            if formatted_text != update.message.text:
                context.bot.send_message(chat_id=update.message.chat_id, text=formatted_text)
    
    except Exception as e:
        logger.error(f'Error processing channel post: {str(e)}')
        context.bot.send_message(chat_id=update.message.chat_id, text='Sorry, there was an error processing your post. Please try again.')

def main() -> None:
    # Start the Flask server in a separate thread
    keep_alive()
    
    # Create the Updater and pass it your bot's token
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('effects', effects_command))

    # Register the message handlers
    dispatcher.add_handler(MessageHandler(Filters.photo & ~Filters.chat_type.channel, image_handler))
    dispatcher.add_handler(MessageHandler((Filters.video | Filters.animation) & ~Filters.chat_type.channel, video_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command & ~Filters.chat_type.channel, text_handler))

    # Register channel post handlers
    dispatcher.add_handler(MessageHandler(Filters.photo & Filters.chat_type.channel, channel_post_handler))
    dispatcher.add_handler(MessageHandler((Filters.video | Filters.animation) & Filters.chat_type.channel, channel_post_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.channel, channel_post_handler))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you send a signal to stop
    updater.idle()

if __name__ == '__main__':
    main()


def channel_post_handler(update: Update, context: CallbackContext) -> None:
    try:
        # Handle photos
        if update.message.photo:
            photo = update.message.photo[-1]
            photo_file = photo.get_file()
            photo_bytes = photo_file.download_as_bytearray()
            processed_image, caption = process_single_image((photo_bytes, update.message.caption or "Join For More ➥ @Thrill_Zone"))
            if processed_image:
                context.bot.send_photo(chat_id=update.message.chat_id, photo=processed_image, caption=caption)
        
        # Handle videos and animations
        elif update.message.video or update.message.animation:
            video = update.message.video or update.message.animation
            video_file = video.get_file()
            video_bytes = video_file.download_as_bytearray()
            processed_video, caption = process_single_video((video_bytes, update.message.caption or "Join For More ➥ @Thrill_Zone", bool(update.message.animation)))
            if processed_video:
                if update.message.animation:
                    context.bot.send_animation(chat_id=update.message.chat_id, animation=processed_video, caption=caption)
                else:
                    context.bot.send_video(chat_id=update.message.chat_id, video=processed_video, caption=caption)
        
        # Handle text messages (Terabox links)
        elif update.message.text:
            formatted_text = format_terabox_links(update.message.text)
            if formatted_text != update.message.text:
                context.bot.send_message(chat_id=update.message.chat_id, text=formatted_text)
    
    except Exception as e:
        logger.error(f'Error processing channel post: {str(e)}')
        context.bot.send_message(chat_id=update.message.chat_id, text='Sorry, there was an error processing your post. Please try again.')
