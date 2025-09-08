"""
This script processes image files in a given directory, generating tags, headlines, and abstracts for each image using an AI model. 
It supports HEIC to JPG conversion and writes metadata back to the images using ExifTool.

Copyright (C) 2025 Tobias Himstedt

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, 
either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. 
If not, see <https://www.gnu.org/licenses/>.
"""
import logging.config
import os
from datetime import datetime
from openai import OpenAI
import exiftool
from exiftool.exceptions import ExifToolException 
import json
from PIL import Image
from pillow_heif import register_heif_opener
import tempfile
import base64
import logging
from logging.handlers import RotatingFileHandler
import argparse
from tqdm import tqdm



TAGS_PROMPT = "generate 5-10 tags in for the given image. Separate tags with commas. Return each tag in English and German language. Just respond with the tags."
HEADLINE_PROMPT = "Generate a headline of the image. Just respond with the headline."
ABSTRACT_PROMPT = "Generate a short abstract of the image. Just respond with the abstract."
logger = logging.getLogger(__name__)

def describe_image_by_model(image_path:str, prompt:str, schema:dict, model:str) -> str:
    """
    Connect to the LLM and get a response for the given image and prompt.
    Args:
        image_path (str): Path to the image file
        prompt (str): Prompt to send to the LLM
        model (str): Model to use for the LLM
    Returns:
        str: The JSON response from the LLM
    """
    logging.info(f"Connecting to LLM with image: {image_path}")
    
    # Debug log: Log the schema being used
    logger.debug(f"Schema being used: {json.dumps(schema, indent=2)}")
    
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    detail="auto"
    
    # Debug log: Log the payload structure
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type":
                        "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}", "detail": detail}}
                ]
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "image description",
                "schema": schema
            }
        }
    }
    
    logger.debug(f"Payload response_format: {json.dumps(payload['response_format'], indent=2)}")
    
    try:
        response = client.chat.completions.create(**payload)
        result = response.choices[0].message.content
        logger.debug(f"Raw LLM response: {result}")
        return result
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        raise

def connect_llm(image_path:str, prompt:str, model:str) -> str:
    logger.info(f"Connecting to LLM with image: {image_path} and prompt: {prompt}")
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    detail="auto"
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}", "detail": detail}}
            ]
        }],
        "max_tokens": 50
    }

    response = client.chat.completions.create(**payload)
    result = response.choices[0].message.content
    return result

def parse_json_result(result:str) -> dict:
    """
    Parse the JSON result from the LLM response.
    
    Args:
        result (str): The JSON string to parse.
        
    Returns:
        dict: The parsed JSON object.
    """
    try:
        # Remove any unwanted characters before parsing
        result = result.strip()
        # Parse the JSON string into a Python dictionary
        parsed_result = json.loads(result)
        return parsed_result
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {str(e)}")
        return {}
    
def generate_image_tags(image_path, model="gemma3:27b"):
    logger.info(f"Generating tags for image: {image_path}")
    tags = connect_llm(image_path, TAGS_PROMPT, model)
    tags = tags.split(",")
    # remove leading and trailing whitespace from each tag
    tags = [tag.strip() for tag in tags]    
    return tags

def generate_image_headline(image_path, model="gemma3:27b"):
    logger.info(f"Generating description for image: {image_path}")
    return connect_llm(image_path, HEADLINE_PROMPT, model)

def generate_image_abstract(image_path, model="gemma3:27b"):
    logger.info(f"Generating abstract for image: {image_path}")
    return connect_llm(image_path, ABSTRACT_PROMPT, model)

def get_image_files(directory):
    """Get list of image files in directory"""
    logger.info(f"Getting image files from directory: {directory}")
    image_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.heic')):
                image_files.append(os.path.join(root, file))
    return image_files

def convert_heic_to_jpg(heic_path):
    """
    Convert a HEIC image to a temporary JPG image.
    
    Args:
        heic_path (str): Path to the input HEIC image file
        
    Returns:
        str: Path to the temporary JPG image file
    """
    logger.info(f"Converting HEIC to temp JPG: {heic_path}")
    try:
        # Open the HEIC image using Pillow
        with Image.open(heic_path) as heic_image:
            # Create a temporary file with .jpg extension
            temp_jpg = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            
            # Save the HEIC image as JPG to the temporary file
            heic_image.save(temp_jpg.name, 'JPEG')
            
            return temp_jpg.name
            
    except Exception as e:
        logger.error(f"Error converting HEIC to JPG: {str(e)}")
        return None

def process_image(image_path:str, model:str, overwrite=False) -> None:
    logger.info(f"Processing image: {image_path}")
    PROMPT = """
        Analyze this image. Respond in json format with the following elements:
        5-10 tags in english language. Separate tags with commas. Append the same tags in german language to the list.
        a headline for the image
        a short abstract of the image
        Return the json object with the following keys:
        Example:
        {
        "tags": ["tag1", "tag2"],
        "headline": "headline",
        "abstract": "abstract"
        }
        Do not add any other text. Just respond with the json object.        
        """

    schema = {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"}
            },
            "headline": {"type": "string"},
            "abstract": {"type": "string"}
        },
        "required": ["tags", "headline", "abstract"]
    }
    try:
        with exiftool.ExifToolHelper(common_args=["-G", "-n", "-P", "-overwrite_original_in_place"]) as helper:
            tags = helper.get_tags(image_path, tags=["XMP-dc:Subject", "IPTC:Keywords"])
            # Check if the image already has tags
            if tags and not overwrite \
                and ("XMP:Subject" in tags[0] or "IPTC:Keywords" in tags[0]):
                logger.info("Image already has tags. Skipping...")
            else:
                jpg_image = image_path
                if image_path.lower().endswith('.heic'):
                    jpg_image = convert_heic_to_jpg(image_path)

                logger.info(f"Processing image with model: {model}")
                json_result = describe_image_by_model(jpg_image, PROMPT, schema, model)
                result = parse_json_result(json_result)
                tags = result.get("tags", [])
                # remove leading and trailing whitespace from each tag
                tags = [tag.strip() for tag in tags]
                headline = result.get("headline", "").strip()
                abstract = result.get("abstract", "").strip()
                logger.debug(f"Tags: {tags}")
                logger.debug(f"Headline: {headline}")
                logger.debug(f"Abstract: {abstract}")
                # tags = generate_image_tags(jpg_image)
                helper.set_tags(image_path, 
                    tags = { 
                        "IPTC:Keywords": tags,
                        "XMP-dc:Subject": tags,
                        "IPTC:Writer-Editor": model,
                        "IPTC:Headline": headline,
                        "XMP-dc:Title": headline,
                        "EXIF:ImageDescription": headline,
                        "IPTC:Caption-Abstract": abstract,
                        "XMP-dc:Description": abstract 
                    }, params=[]
                )
    except Exception as e:
        logger.error(f"ExifTool execution error: {str(e)}")

def process_image_old(image_path:str, model:str, overwrite=False) -> None:
    """Process a single image file"""
    logger.info(f"Processing image: {image_path}")
    # Check if the file exists
    if not os.path.isfile(image_path):
        logger.error(f"The file does not exist: {image_path}")
        return

    jpg_image = image_path
    if image_path.lower().endswith('.heic'):
        jpg_image = convert_heic_to_jpg(image_path)

    try:
        with exiftool.ExifToolHelper() as helper:
            tags = helper.get_tags(image_path, tags=["XMP-dc:Subject", "IPTC:Keywords"])
            # Check if the image already has tags   
            if tags and not overwrite and ("XMP:Subject" in tags[0] or "IPTC:Keywords" in tags[0]):
                logger.info("Image already has tags. Skipping...")
            else:
                tags = generate_image_tags(jpg_image)
                helper.set_tags(image_path, 
                    tags = { 
                        "IPTC:Keywords": tags,
                        "XMP-dc:Subject": tags,
                        "IPTC:Writer-Editor": model
                    }, params=[]
                )

            # Check if the image already has a description
            headline = helper.get_tags(image_path, tags=["XMP-dc:Title", "IPTC:Headline"])
            if headline and not overwrite and ("XMP:Title" in headline[0] or "IPTC:Headline" in headline[0]):
                logger.info("Image already has description. Skipping...")
            else:
                headline = generate_image_headline(jpg_image)
                helper.set_tags(image_path, 
                    tags = { 
                        "IPTC:Headline": headline,
                        "XMP-dc:Title": headline,
                        "IPTC:Writer-Editor": model
                    }, params=[]
                )
            # Check if the image already has an abstract
            abstract = helper.get_tags(image_path, tags=["XMP-dc:Description", "IPTC:Caption-Abstract"])
            if abstract and not overwrite and ("XMP:Description" in abstract[0] or "IPTC:Caption-Abstract" in abstract[0]):
                logger.info("Image already has abstract. Skipping...")
            else:
                abstract = generate_image_abstract(jpg_image)
                helper.set_tags(image_path, 
                    tags = { 
                        "IPTC:Caption-Abstract": abstract,
                        "XMP-dc:Description": abstract,
                        "IPTC:Writer-Editor": model
                    }, params=[]
                )
    except Exception as e:
        logger.error(f"ExifTool execution error: {str(e)}")

def run(directory:str, model:str, overwrite:bool=False) -> None:
    """Main function to process all images in directory"""
    register_heif_opener()

    image_files = get_image_files(directory)
    
    counter = 0
    total = len(image_files)
    for image_path in tqdm(image_files, desc="Processing images...", leave=False):
        process_image(image_path, model=model, overwrite=overwrite)
        logger.info(f"Processed {counter}/{total} images")
        counter += 1
        # process_image(image_path, model, overwrite)
    logger.info(f"Processed {total} images in directory: {directory}")

def main():
    global client, log_file, verbose

    parser = argparse.ArgumentParser(description='My script description')
    parser.add_argument('directory', type=str, help='Directory to process', default= ".")
    parser.add_argument('--model', type=str, help='Model to use', default="gemma3:27b")
    parser.add_argument('--overwrite', action=argparse.BooleanOptionalAction, help='Overwrite existing tag, headline and abstract', default=False)
    parser.add_argument('--ai_server', type=str, help='URL of AI server to use', required=True)
    parser.add_argument('--api_key', type=str, help='API key to use', required=True)
    parser.add_argument('--log_file', type=str, help='Where to put the log file', default="/var/log/photo_tagger.log")
    parser.add_argument('--verbose', action=argparse.BooleanOptionalAction, help='Log tag, headline and description', default=False)

    args = parser.parse_args()
    directory = args.directory
    model = args.model
    overwrite = args.overwrite
    ai_server = args.ai_server
    api_key = args.api_key
    log_file = args.log_file
    verbose = args.verbose
    # Configure logging to file
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(log_file, maxBytes=10**7, backupCount=5),
            logging.StreamHandler()
        ]
    )
    # set log level to DEBUG if verbose is True
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    client = OpenAI(base_url=ai_server, api_key=api_key)
    run(directory, model=model, overwrite=overwrite)

if __name__ == "__main__":
    main()

