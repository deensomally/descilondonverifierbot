import logging
from telegram import Update, ChatJoinRequest
from telegram.ext import Application, ChatJoinRequestHandler, MessageHandler, filters, CallbackContext
import requests
from bs4 import BeautifulSoup
import re

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Your verification message
VERIFICATION_MESSAGE = """
Hey

Thanks for requesting to join the @DeSciLondon telegram

I'm the admin, nice to meet you!

Do you mind telling me a little bit about yourself and sharing some socials (eg twitter/linkedIn)

We get a lot of spam accounts/bots trying to join the group hence we need to prove you're a real human!
"""

# Dictionary to track pending join requests (user_id: join_request)
pending_requests = {}

def extract_links(text):
    """Extract URLs from message text."""
    url_pattern = re.compile(r'(https?://[^\s]+)')
    return url_pattern.findall(text)

def verify_links(links):
    """Basic verification: Check if social profiles exist and seem active.
    - For Twitter/X: Check if URL loads and has tweets/followers.
    - For LinkedIn: Check if URL loads and has content.
    Returns True if at least one link seems real (customize thresholds).
    """
    for link in links:
        try:
            if 'twitter.com' in link or 'x.com' in link:
                # Normalize to x.com
                link = link.replace('twitter.com', 'x.com')
                response = requests.get(link, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Check for signs of activity (e.g., presence of tweets or followers count)
                    if soup.find(attrs={'data-testid': 'primaryColumn'}):  # Rough check for profile content
                        return True
            elif 'linkedin.com' in link:
                response = requests.get(link, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Check for profile elements (e.g., name or posts)
                    if soup.find('h1', class_='top-card-layout__title'):  # LinkedIn profile header
                        return True
            # Add more socials if needed (e.g., GitHub, etc.)
        except Exception as e:
            logger.error(f"Error verifying {link}: {e}")
    return False  # If no valid links or all fail

async def handle_join_request(update: Update, context: CallbackContext) -> None:
    """Handle new join request: Send verification message and store request."""
    join_request: ChatJoinRequest = update.chat_join_request
    user_id = join_request.from_user.id
    chat_id = join_request.chat.id
    
    # Send verification message to the user
    await context.bot.send_message(chat_id=user_id, text=VERIFICATION_MESSAGE)
    
    # Store the request for later approval
    pending_requests[user_id] = join_request
    logger.info(f"Sent verification to user {user_id}")

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handle responses: Check links and approve if verified."""
    user_id = update.message.from_user.id
    text = update.message.text
    
    if user_id in pending_requests:
        links = extract_links(text)
        if links and verify_links(links):
            join_request = pending_requests.pop(user_id)
            await join_request.approve()
            await update.message.reply_text("Thanks! Verified as real. Welcome to the group!")
            logger.info(f"Approved user {user_id}")
        else:
            await update.message.reply_text("Sorry, couldn't verify. Please provide valid social links or more info.")
            logger.info(f"Rejected user {user_id}")
    else:
        # Ignore non-pending messages (optional: add bot commands)
        pass

def main() -> None:
    """Start the bot."""
    application = Application.builder().token("8632956978:AAHmurJWkocw-OlthA1K--SYKlRifa1D_7E").build()
    
    # Handler for join requests
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    # Handler for private messages (responses)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()