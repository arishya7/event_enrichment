import json
from typing import Dict, Optional, List, Any
from pathlib import Path
from dotenv import load_dotenv
import os
from google import genai
from google.generativeai.types import GenerationConfig
from PIL import Image

load_dotenv()

class GeminiImageSelector:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY") 
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env file")
        
        self.client = genai.Client(api_key=self.api_key)

    def rank_images(self, title: str, images_info: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Ranks all images from best (1) to worst (n) using Gemini.
        
        Args:
            title: Event title
            images_info: List of image details with local_path and original_url
        Returns:
            Dict[str, int]: Mapping of image URLs to their rank (1 is best)
        """
        if not images_info:
            return {}

        num_images = len(images_info)
        prompt = [
            "Rank these images from best (1) to worst ({num_images}) for this event listing.",
            f"Event Title: {title}",
            "Consider visual appeal and relevance to the event.",
            f"Respond ONLY with a JSON mapping URLs to ranks 1-{num_images}:",
            "{\"image_rankings\": {\"<url1>\": 1, \"<url2>\": 2, ...}}",
            "Every image MUST have a unique rank from 1 to {num_images}."
        ]

        valid_images = []
        url_to_info = {}

        for img_info in images_info:
            local_path = Path(img_info['local_path'])
            if not local_path.is_absolute():
                local_path = Path.cwd() / local_path

            if local_path.exists():
                try:
                    img = Image.open(local_path)
                    valid_images.append(img)
                    url_to_info[img_info['original_url']] = img_info
                except Exception as e:
                    print(f"Error loading image {local_path}: {e}")

        if not valid_images:
            return {}

        try:
            response = self.client.models.generate_content(
                model="gemini-1.5-flash-latest",
                contents=["\n".join(prompt), *valid_images],
                generation_config=GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            if response and response.text:
                data = json.loads(response.text)
                rankings = data.get("image_rankings", {})
                
                # Verify rankings are valid (1 to num_images)
                used_ranks = set(rankings.values())
                expected_ranks = set(range(1, len(valid_images) + 1))
                
                if used_ranks == expected_ranks and all(url in url_to_info for url in rankings):
                    return rankings

        except Exception as e:
            print(f"Error during Gemini API call: {e}")

        return {}

def main():
    blog_test = "sassymamasg"
    images_dir = Path(f"events_output/images/{blog_test}")
    images_dir.mkdir(parents=True, exist_ok=True)  # This will create all parent directories
    mapping_file = Path("events_output/images/image_mapping.json")

    if not mapping_file.exists():
        print(f"Image mapping file not found: {mapping_file}")
        return

    try:
        with open(mapping_file) as f:
            image_mapping = json.load(f)
    except Exception as e:
        print(f"Error loading image mapping: {e}")
        return

    try:
        selector = GeminiImageSelector()
    except ValueError as e:
        print(f"Error initializing Gemini: {e}")
        return

    rankings_by_event = {}

    for title, images in image_mapping.items():
        print(f"Ranking images for: {title}")
        rankings = selector.rank_images(title, images)
        if rankings:
            rankings_by_event[title] = rankings

    output_file = images_dir / "image_rankings.json"
    with open(output_file, 'w') as f:
        json.dump(rankings_by_event, f, indent=2)

if __name__ == "__main__":
    main() 