"""
Feed Manager for RSS/Atom Feed Management

This module provides a comprehensive interface for managing RSS and Atom feeds
in the Event JSON & Image Editor application. It includes XML validation,
feed statistics analysis, and interactive feed management capabilities.

"""

import streamlit as st
from pathlib import Path
import xml.etree.ElementTree as ET
import json

# Load configuration from config file
with open("config/config.json", 'r', encoding='utf-8') as f:
    config = json.loads(f.read())

def validate_xml(xml_content):
    """
    Validate if the provided content is valid XML with detailed error reporting.
    
    Performs comprehensive XML validation for RSS and Atom feeds, including:
    - Basic XML syntax validation
    - Feed type detection (RSS vs Atom)
    - Common XML formatting issues
    - Detailed error messages with line/column information
    
    The validation checks for:
    - Proper XML declaration
    - Valid XML syntax
    - RSS or Atom root elements
    - Leading whitespace issues
    - Common parsing errors
    
    Args:
        xml_content (str): XML content to validate
        
    Returns:
        tuple: (is_valid, error_message) where is_valid is boolean
        
    Example:
        is_valid, message = validate_xml(rss_content)
        if is_valid:
            print("Valid RSS feed")
        else:
            print(f"Invalid: {message}")
    """
    if not xml_content or not xml_content.strip():
        return False, "No content provided"
    
    try:
        # Check for common issues first
        content = xml_content.strip()
        
        # Check if content starts with XML declaration or root element
        if not content.startswith('<?xml') and not content.startswith('<'):
            return False, "Content doesn't appear to be XML (must start with <?xml or <)"
        
        # Check for leading whitespace before XML declaration
        if content.startswith('<?xml') and xml_content.startswith((' ', '\t', '\n', '\r')):
            return False, "XML declaration must be at the very beginning (remove leading whitespace)"
        
        # Try to parse the XML
        root = ET.fromstring(content)
        
        # Additional checks for RSS/Atom feeds
        root_tag = root.tag.lower()
        if 'rss' not in root_tag and 'feed' not in root_tag:
            return False, f"This doesn't appear to be an RSS or Atom feed (root element: {root.tag})"
        
        return True, "Valid XML feed"
        
    except ET.ParseError as e:
        # Provide more detailed error information
        error_msg = str(e)
        line_info = ""
        
        # Extract line and column information if available
        if "line" in error_msg and "column" in error_msg:
            line_info = " " + error_msg.split(":")[1].strip() if ":" in error_msg else ""
        
        return False, f"XML Parse Error{line_info}: {error_msg}"
    
    except Exception as e:
        return False, f"Validation Error: {str(e)}"

def get_feed_stats(xml_content):
    """
    Get basic statistics about the XML feed.
    
    Analyzes the XML content to determine feed type and count articles.
    Supports both RSS and Atom feed formats with automatic detection.
    
    The function provides:
    - Feed type identification (RSS or Atom)
    - Article/entry count
    - Basic feed structure analysis
    
    Args:
        xml_content (str): XML feed content to analyze
        
    Returns:
        str: Formatted statistics string with feed type and article count
        
    Example:
        stats = get_feed_stats(rss_content)
        # Returns: "📊 **Feed Type:** RSS | **Articles Found:** 25"
    """
    try:
        root = ET.fromstring(xml_content)
        
        # Check if it's Atom or RSS
        root_tag = root.tag
        is_atom = (root_tag == '{http://www.w3.org/2005/Atom}feed' or 
                   root_tag.endswith('}feed') or
                   'atom' in root_tag.lower())
        
        # Count entries/items
        if is_atom:
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            feed_type = "Atom"
        else:
            entries = root.findall('.//item')
            feed_type = "RSS"
            
        return f"📊 **Feed Type:** {feed_type} | **Articles Found:** {len(entries)}"
    except:
        return "📊 **Feed analysis not available**"

def main():
    """
    Main feed manager interface.
    
    Provides a comprehensive Streamlit interface for managing RSS and Atom feeds.
    The interface includes:
    - Blog source selection
    - XML feed input and validation
    - Feed statistics display
    - Feed storage and management
    - Error handling and user feedback
    
    Features:
    - Multi-blog support with sidebar selection
    - Real-time XML validation
    - Feed statistics analysis
    - Temporary feed storage
    - Interactive error reporting
    """
    st.set_page_config(
        page_title="Feed Manager",
        page_icon="📰",
        layout="wide"
    )
    
    st.title("📰 Manual Feed Manager")
    st.markdown("Paste and manage XML feeds for each blog manually.")
    
    # Create temp feed directory if it doesn't exist
    temp_feed_dir = Path(config["paths"]['temp_feed'])
    temp_feed_dir.mkdir(parents=True, exist_ok=True)
    
    # Get list of blogs from config
    website = {}
    blogs = []
    for blog_name, blog_url in config['blog_website'].items():
        blogs.append(blog_name)
        website[blog_name] = blog_url
    
    if not blogs:
        st.error("No blogs found in configuration!")
        return
    
    # Sidebar for blog selection
    st.sidebar.header("📚 Select Blog")
    selected_blog = st.sidebar.selectbox("Choose a blog:", blogs)
    
    if selected_blog:
        st.header(f"Managing: **{selected_blog}**")
        st.write(f"Feed website: {website[selected_blog]}")
        
        # File path for this blog's feed
        feed_file = temp_feed_dir / f"{selected_blog}.xml"
        
        # Check if file already exists
        existing_content = ""
        if feed_file.exists():
            try:
                with open(feed_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                st.success(f"✅ Existing feed file found: `{feed_file}`")
                
                # Show stats for existing content
                if existing_content:
                    st.markdown(get_feed_stats(existing_content))
                    
            except Exception as e:
                st.error(f"❌ Error reading existing file: {str(e)}")
        else:
            st.info(f"ℹ️ No existing feed file found. Will create: `{feed_file}`")
        
        # Create tabs for different actions
        tab1, tab2, tab3 = st.tabs(["📝 Edit Feed", "👀 Preview", "📁 File Manager"])
        
        with tab1:
            st.subheader("XML Feed Content")
            
            # Text area for XML content
            xml_content = st.text_area(
                "Paste your XML feed content here:",
                value=existing_content,
                height=600,
                help="Paste the complete XML content from the blog's RSS/Atom feed"
            )
            
            # Auto-validation feedback (only if content exists and is different from existing)
            if xml_content.strip() and xml_content.strip() != existing_content.strip():
                with st.expander("🔍 **Live Validation**", expanded=True):
                    is_valid, message = validate_xml(xml_content)
                    if is_valid:
                        st.success(f"✅ {message}")
                        st.markdown(get_feed_stats(xml_content))
                    else:
                        st.error(f"❌ {message}")
                        if "leading whitespace" in message.lower():
                            st.info("💡 Try removing blank lines at the beginning")
                        elif "parse error" in message.lower():
                            st.info("💡 Check your XML syntax")
            elif xml_content.strip() and xml_content.strip() == existing_content.strip():
                # Show stats for unchanged existing content
                if xml_content.strip():
                    st.markdown(f"📊 **Current Feed:** {get_feed_stats(xml_content)}")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("💾 Save Feed", type="primary"):
                    if xml_content.strip():
                        # Always validate XML before saving
                        st.info("🔍 Validating XML content...")
                        is_valid, message = validate_xml(xml_content)
                        
                        if is_valid:
                            try:
                                # Save the validated content
                                with open(feed_file, 'w', encoding='utf-8') as f:
                                    f.write(xml_content.strip())  # Save trimmed content
                                st.success(f"✅ Feed saved successfully to `{feed_file}`")
                                st.success(f"✅ {message}")
                                st.markdown(get_feed_stats(xml_content))
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error saving file: {str(e)}")
                        else:
                            # Show validation error in popup (same as validate button)
                            st.session_state['validation_result'] = {
                                'is_valid': is_valid,
                                'message': message,
                                'xml_content': xml_content,
                                'action': 'save'  # Flag to show it's from save action
                            }
                            st.rerun()
                    else:
                        st.toast("⚠️ Please enter some XML content before saving.", icon="⚠️")
            
            with col2:
                if st.button("🔍 Validate XML"):
                    if xml_content.strip():
                        # Store validation result in session state to trigger modal
                        is_valid, message = validate_xml(xml_content)
                        st.session_state['validation_result'] = {
                            'is_valid': is_valid,
                            'message': message,
                            'xml_content': xml_content,
                            'action': 'validate'  # Flag to show it's from validate action
                        }
                    else:
                        st.toast("⚠️ Please enter some XML content to validate.", icon="⚠️")
            
            with col3:
                if feed_file.exists():
                    if st.button("🗑️ Delete Feed", help="Delete the current feed file"):
                        try:
                            feed_file.unlink()
                            st.success("✅ Feed file deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error deleting file: {str(e)}")
        
        with tab2:
            st.subheader("XML Preview")
            if xml_content.strip():
                # Show formatted XML
                try:
                    # Parse and reformat XML for better display
                    root = ET.fromstring(xml_content)
                    # Display first few characters with syntax highlighting
                    st.code(xml_content[:2000] + ("..." if len(xml_content) > 2000 else ""), language="xml")
                    
                    if len(xml_content) > 2000:
                        st.info(f"📏 Showing first 2000 characters. Total length: {len(xml_content)} characters")
                        
                    # Show feed analysis
                    st.markdown("---")
                    st.markdown(get_feed_stats(xml_content))
                    
                except Exception as e:
                    st.error(f"❌ Cannot preview XML: {str(e)}")
                    st.code(xml_content[:1000] + ("..." if len(xml_content) > 1000 else ""), language="text")
            else:
                st.info("ℹ️ No content to preview. Add some XML content in the Edit tab.")
        
        with tab3:
            st.subheader("File Manager")
            
            # Show all existing feed files
            feed_files = list(temp_feed_dir.glob("*.xml"))
            
            if feed_files:
                st.markdown("**📁 Existing Feed Files:**")
                for file in feed_files:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        file_size = file.stat().st_size
                        st.markdown(f"📄 `{file.name}` ({file_size:,} bytes)")
                    
                    with col2:
                        if st.button(f"📂 Load", key=f"load_{file.name}"):
                            # Load this file's content
                            try:
                                with open(file, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                st.session_state['loaded_content'] = content
                                st.success(f"✅ Loaded {file.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error loading {file.name}: {str(e)}")
                    
                    with col3:
                        if st.button(f"🗑️ Delete", key=f"del_{file.name}"):
                            try:
                                file.unlink()
                                st.success(f"✅ Deleted {file.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error deleting {file.name}: {str(e)}")
            else:
                st.info("ℹ️ No feed files found in the temp directory.")
                
            # Show directory info
            st.markdown("---")
            st.markdown(f"**📂 Feed Directory:** `{temp_feed_dir.absolute()}`")
            
    # Instructions
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📖 Instructions")
    st.sidebar.markdown("""
    1. **Select a blog** from the dropdown
    2. **Paste XML content** in the Edit tab
    3. **Validate** the XML format
    4. **Save** the feed file
    5. The file will be used by the main application
    """)
    
    st.sidebar.markdown("### 💡 Tips")
    st.sidebar.markdown("""
    - Copy XML from the blog's RSS/Atom feed URL
    - Ensure the XML is complete and valid
    - Use the Preview tab to check content
    - Files are saved as `{blog_name}.xml`
    """)
    
    # Validation Results Modal (placed at end to avoid layout interference)
    # Handle both validation button and save button results
    if 'validation_result' in st.session_state:
        validation_data = st.session_state['validation_result']
        action = validation_data.get('action', 'validate')
        
        # Set modal title based on action
        modal_title = "❌ Save Failed - Validation Error" if action == 'save' else "🔍 XML Validation Results"
        
        @st.dialog(modal_title)
        def show_validation_popup():
            if validation_data['is_valid']:
                st.success(f"✅ **Validation Passed**") 
                st.markdown(f"{get_feed_stats(validation_data['xml_content'])}")
                
            else:
                # Different messaging based on action
                if action == 'save':
                    st.error("❌ **Cannot Save Feed - Validation Failed**")
                else:
                    st.error("❌ **Validation Failed**")
                
                st.error(f"**Error Details:** {validation_data['message']}")
                
                st.markdown("---")
                st.markdown("💡 **Troubleshooting Tips:**")
                
                # Provide helpful tips based on the error
                if "leading whitespace" in validation_data['message'].lower():
                    st.warning("🔧 Remove any blank lines or spaces before the XML declaration `<?xml version=...`")
                elif "doesn't appear to be xml" in validation_data['message'].lower():
                    st.warning("🔧 Make sure you're pasting XML content from an RSS or Atom feed URL")
                elif "rss or atom feed" in validation_data['message'].lower():
                    st.warning("🔧 This should be RSS (starting with `<rss>`) or Atom (starting with `<feed>`) content")
                elif "parse error" in validation_data['message'].lower():
                    st.warning("🔧 Check for missing closing tags, special characters, or incomplete XML structure")
                
            
            # Close button
            if st.button("Close", type="primary"):
                del st.session_state['validation_result']
                st.rerun()
        
        show_validation_popup()

if __name__ == "__main__":
    main() 