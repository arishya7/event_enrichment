class OutputFormatter:
    """Utility class for clean, formatted console output with tree-like structure."""
    
    def __init__(self):
        self.indent_level = 0
        
    def print_header(self, text: str, width: int = 50):
        """Print a header with equal signs."""
        print("\n" + "=" * width)
        print(f"🕒 {text}")
        print("=" * width + "\n")
    
    def print_section(self, title: str):
        """Print a section title."""
        print(f"📚 {title}")
        print("┌─────────────────────────────────────────")
    
    def print_item(self, text: str):
        """Print an item in a list."""
        print(f"│ • {text}")
    
    def print_section_end(self):
        """Print section end."""
        print("└─────────────────────────────────────────")
    
    def print_box_start(self, title: str, width: int = 60):
        """Print the start of a processing box."""
        header_text = f"─ Processing: {title.upper()} "
        remaining_dashes = width - len(header_text) - 1
        top_line = f"┌{header_text}" + "─" * remaining_dashes
        print(f"\n{top_line}")
        return "└" + "─" * (width - 1)  # Return bottom line for later use
    
    def print_box_end(self, bottom_line: str):
        """Print the end of a processing box."""
        print(bottom_line)
    
    def print_level1(self, text: str):
        """Print at level 1 indentation (│)."""
        print(f"│ {text}")
    
    def print_level2(self, text: str):
        """Print at level 2 indentation (│ │)."""
        print(f"│ │ {text}")
    
    def print_level3(self, text: str):
        """Print at level 3 indentation (│ │ │)."""
        print(f"│ │ │ {text}")
    
    def print_article_start(self, idx: int, total: int):
        """Print article processing start."""
        dashes = "─" * (30 - len(str(idx)) - len(str(total)))
        print(f"│ ┌─ Article {idx}/{total} {dashes}", flush=True)
    
    def print_article_end(self):
        """Print article processing end."""
        print("│ └─────────────────────────────────────────")
    
    def print_event_start(self, idx: int, total: int):
        """Print event processing start."""
        dashes = "─" * (25 - len(str(idx)) - len(str(total)))
        print(f"│ │ ┌─ Event {idx}/{total} {dashes}")
    
    def print_event_end(self):
        """Print event processing end."""
        print(f"│ │ └" + "─" * 35)
    
    def print_success(self, text: str, level: int = 1):
        """Print success message with checkmark."""
        prefix = "│ " * level
        print(f"{prefix}✅ {text}")
    
    def print_error(self, text: str, level: int = 1):
        """Print error message with X mark."""
        prefix = "│ " * level
        print(f"{prefix}❌ {text}")
    
    def print_info(self, text: str, level: int = 1):
        """Print info message with info icon."""
        prefix = "│ " * level
        print(f"{prefix}ℹ️  {text}")
    
    def print_warning(self, text: str, level: int = 1):
        """Print warning message with warning icon."""
        prefix = "│ " * level
        print(f"{prefix}⚠️  {text}")
    
    def print_processing(self, text: str, level: int = 1):
        """Print processing message with gear icon."""
        prefix = "│ " * level
        print(f"{prefix}⚙️  {text}")

# Create a global instance for easy access
formatter = OutputFormatter() 