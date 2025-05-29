import json

def load_rss(file_path):
    """Load and parse JSON data from RSS output file.
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        dict: Parsed JSON data as a dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None
    
def extract_article(rss_data):
    articles = rss_data.get('articles', [])
    return articles


if __name__ == "__main__":
    # Test the RSS loading functionality
    rss_data = load_rss("RSS_output/sassymamasg.json")
    print(type(rss_data))
    
    print(type(extract_article(rss_data)[0]))
    print(extract_article(rss_data)[1].keys())