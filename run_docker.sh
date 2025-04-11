docker run -v ./:/var/log -v YOUR_PHOTO_DIR:/app/images hulk66/photo-tagging python tagger.py --ai_server YOUR_AI_SERVER --api_key YOUR_API__KEY --model YOUR_MODEL /app/images
# Example
docker run -v ./:/var/log -v /mnt/user/photos:/app/images hulk66/photo-tagging python tagger.py --ai_server http://ollama:11434/v1 --model gemma3:27b --api_key SK_12345 /app/images
