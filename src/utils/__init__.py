# Import classes and functions individually to avoid circular imports
from .config import config, dict_to_namespace, load_json_file, load_text_file
from .text_utils import (
    simple_text_to_id, extract_post_id, extract_post_id_atom, 
    clean_html, clean_text, extract_urls, is_valid_json, preserve_links_html
)
from .url_utils import validate_url
from .timeout_utils import TimeoutError, run_with_timeout, timeout_decorator, gemini_generate_text
from .output_formatter import OutputFormatter
from .file_utils import (
    save_to_json, download_image, edit_prompt_interactively, 
    cleanup_temp_folders
)
from .import_from_excel import (
    reconstruct_json_event, import_excel_to_json_directory, 
    import_excel_to_json
)
from .export_to_excel import (
    flatten_json_event, open_excel_file, export_directory_to_excel, 
    export_json_to_excel
)

# Create a formatter instance for easy access
formatter = OutputFormatter()

# Define what should be imported with 'from src.utils import *'
__all__ = [
    # Config
    'config',
    'dict_to_namespace',
    'load_json_file', 
    'load_text_file',
    
    # Text Utils
    'simple_text_to_id',
    'extract_post_id',
    'extract_post_id_atom',
    'clean_html',
    'clean_text',
    'extract_urls',
    'is_valid_json',
    'preserve_links_html',
    
    # URL Utils
    'validate_url',
    
    # Timeout Utils
    'TimeoutError',
    'run_with_timeout',
    'timeout_decorator',
    'gemini_generate_text',
    
    # Output Formatter
    'OutputFormatter',
    'formatter',
    
    # File Utils
    'save_to_json',
    'download_image',
    'edit_prompt_interactively',
    'cleanup_temp_folders',
    
    # Import/Export Utils
    'reconstruct_json_event',
    'import_excel_to_json_directory',
    'import_excel_to_json',
    'flatten_json_event',
    'open_excel_file',
    'export_directory_to_excel',
    'export_json_to_excel'
] 