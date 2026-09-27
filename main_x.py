import asyncio
from twitter_bot import TwitterBotEngine

async def main():
    # Initialize the engine
    bot = TwitterBotEngine()
    
    # Define your post content and optional media file path (set media to None for text-only)
    content = "Automated system test via dedicated engine. Scaling up execution. 🚀 #automation #buildinpublic"
    media_file = None  # Example: "path/to/image.jpg"
    
    # Run the mass broadcast
    await bot.broadcast_macro(tweet_text=content, media_path=media_file)

if __name__ == "__main__":
    asyncio.run(main())
