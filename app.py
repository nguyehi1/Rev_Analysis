import streamlit as st
from pathlib import Path
import sys
import base64
import os
import pandas as pd
import plotly.express as px
import logging
from typing import Optional

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from utils.pdf_extractor import extract_text_from_pdf
from utils.llm_analyzer import extract_and_analyze_combined, set_api_key, identify_contract_type

# Constants
MAX_FILE_SIZE_MB = 20
SUPPORTED_FILE_TYPES = ['pdf']

# Page configuration
st.set_page_config(
    page_title="ASC 606 Contract Analyzer",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def _load_local_css(css_path: Path) -> None:
    """Load local CSS with error handling."""
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            logger.debug(f"✓ Loaded CSS from {css_path}")
    except FileNotFoundError:
        logger.warning(f"CSS file not found: {css_path}")
    except Exception as e:
        logger.error(f"Error loading CSS: {e}")


def _validate_uploaded_file(uploaded_file) -> Optional[str]:
    """Validate uploaded file and return error message if invalid."""
    if uploaded_file is None:
        return None
    
    # Check file size
    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return f"File too large: {uploaded_file.size / (1024*1024):.1f}MB (max: {MAX_FILE_SIZE_MB}MB)"
    
    # Check file type
    if uploaded_file.type != "application/pdf":
        return f"Invalid file type: {uploaded_file.type}. Only PDF files are supported."
    
    # Check file name
    if not uploaded_file.name.lower().endswith('.pdf'):
        return "Invalid file extension. Only PDF files are supported."
    
    return None


def _render_topbar(connected: bool) -> None:
    status = (
        "<span class='status-badge ok'>Gemini Connected</span>"
        if connected else "<span class='status-badge warn'>No API Key</span>"
    )
    st.markdown(
        f"""
        <div class="topbar">
            <div class="brand">
                <span>Revenue Recognition Analyzer</span>
            </div>
            <div class="top-actions">
                {status}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Initialize API key from secrets or environment with better error handling
def _initialize_api_key() -> Optional[str]:
    """Initialize API key from various sources."""
    api_key = None
    
    # Try Streamlit secrets first
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if api_key:
            logger.info("API key loaded from Streamlit secrets")
    except Exception as e:
        logger.debug(f"No Streamlit secrets available: {e}")
    
    # Fall back to environment variable
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            logger.info("API key loaded from environment variable")
    
    return api_key.strip() if api_key else None


# Load CSS and initialize
_load_local_css(Path(__file__).parent / "assets" / "styles.css")

if 'api_key' not in st.session_state:
    st.session_state.api_key = _initialize_api_key()

api_key = st.session_state.api_key

if api_key:
    try:
        set_api_key(api_key)
        logger.info("✓ API key configured successfully")
    except Exception as e:
        logger.error(f"Error setting API key: {e}")
        st.session_state.api_key = None
        api_key = None

# Cache PDF text extraction to avoid re-running
@st.cache_data(show_spinner=False)
def cached_extract_text(pdf_path: str) -> str:
    """Cache PDF text extraction."""
    return extract_text_from_pdf(pdf_path)


# Cache PDF display to avoid re-encoding
@st.cache_data(show_spinner=False)
def get_pdf_display_html(pdf_path: str) -> str:
    """Cache PDF display HTML."""
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    return f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1000" type="application/pdf"></iframe>'

# Initialize session state
if 'contract_text' not in st.session_state:
    st.session_state.contract_text = None
if 'contract_type_info' not in st.session_state:
    st.session_state.contract_type_info = None
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'asc606_analysis' not in st.session_state:
    st.session_state.asc606_analysis = None

# Check if API key is set
_render_topbar(bool(api_key))

# API key onboarding: show a clean connect panel if key is missing
if not api_key:
    with st.expander("Connect to Gemini to enable analysis", expanded=True):
        st.caption("Your key is used only for this session and not stored server-side.")
        key_input = st.text_input("Gemini API Key", type="password", placeholder="AIza...", help="Set GEMINI_API_KEY as an env var to avoid entering it here.")
        cols = st.columns([1, 3])
        with cols[0]:
            if st.button("Save API Key", type="primary", use_container_width=True):
                if key_input:
                    st.session_state.api_key = key_input
                    set_api_key(key_input)
                    st.success("API key saved. You can start analyzing.")
                    st.rerun()
        with cols[1]:
            st.caption("Tip: You can also set this via environment variable GEMINI_API_KEY or Streamlit secrets.")

    st.stop()

# Create 2-column layout from the start: Left = Upload & Analysis, Right = PDF Viewer
col_left, col_right = st.columns([1, 1], gap="medium")

with col_left:
    # File uploader with validation
    uploaded_file = st.file_uploader(
        "Upload Contract",
        type=SUPPORTED_FILE_TYPES,
        help="Upload a SaaS contract in PDF format (max 20MB)"
    )
    
    # Validate uploaded file
    file_error = _validate_uploaded_file(uploaded_file)
    if file_error:
        st.error(file_error)
        uploaded_file = None

if uploaded_file is not None:
    # Generate a unique key for the uploaded file
    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
    
    # Check if this is a new file
    if 'current_file_key' not in st.session_state or st.session_state.current_file_key != file_key:
        # Reset session state for new file
        st.session_state.current_file_key = file_key
        st.session_state.contract_text = None
        st.session_state.contract_type_info = None
        st.session_state.extracted_data = None
        st.session_state.asc606_analysis = None
        st.session_state.temp_pdf_path = None
    
    # Save PDF once if not already saved
    if st.session_state.temp_pdf_path is None:
        temp_pdf_path = Path("data/contracts") / uploaded_file.name
        temp_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_pdf_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        st.session_state.temp_pdf_path = str(temp_pdf_path)
    
    temp_pdf_path = st.session_state.temp_pdf_path
    
    # Continue in left column
    with col_left:
        # Extract text in background if not already done (using cache)
        if st.session_state.contract_text is None:
            with st.spinner("Extracting text from PDF..."):
                try:
                    st.session_state.contract_text = cached_extract_text(temp_pdf_path)
                    logger.info("✓ PDF text extraction successful")
                    st.rerun()
                except Exception as e:
                    logger.error(f"PDF extraction failed: {e}")
                    st.error(f"Failed to extract text from PDF: {str(e)}")
                    st.stop()
    
        # Step 1: Identify contract type
        if st.session_state.contract_type_info is None:
            st.markdown("### Step 1: Identify Contract Type")
            st.info("Click below to identify what type of contract this is.")
            if st.button("Identify Contract Type", type="primary"):
                with st.spinner("Analyzing contract type..."):
                    try:
                        type_info = identify_contract_type(st.session_state.contract_text)
                        st.session_state.contract_type_info = type_info
                        logger.info(f"✓ Contract type identified: {type_info.get('contract_type')}")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Validation error: {str(e)}")
                        logger.error(f"Contract type identification validation failed: {e}")
                    except Exception as e:
                        st.error(f"Failed to identify contract type: {str(e)}")
                        logger.error(f"Contract type identification failed: {e}")

        # Display contract type if identified
        if st.session_state.contract_type_info:
            st.markdown("### Step 1: Contract Type")
            type_info = st.session_state.contract_type_info

            contract_type = type_info.get('contract_type', 'Unknown')
            confidence = (type_info.get('confidence') or 'low').lower()
            reasoning = type_info.get('reasoning', 'N/A')
            indicators = type_info.get('key_indicators') or []

            # Map confidence to pill style
            pill_class = {
                'high': 'pill--high',
                'medium': 'pill--medium',
                'low': 'pill--low'
            }.get(confidence, 'pill--low')

            chips_html = ''.join([f"<span class='chip'>{ind}</span>" for ind in indicators])
            banner_html = f"""
            <div class="type-banner">
              <div class="type-row">
                <div>
                  <div class="type-value">{contract_type}</div>
                </div>
                <div class="pill {pill_class}">{confidence.title()} confidence</div>
              </div>
              <div class="type-title">Reasoning</div>
              <div class="type-reason">{reasoning}</div>
              {f"<div class='type-title' style='margin-top:8px;'>Key indicators</div><div class='chips'>{chips_html}</div>" if indicators else ''}
            </div>
            """
            st.markdown(banner_html, unsafe_allow_html=True)
            st.markdown("---")
        
        # Step 2: Full ASC 606 Analysis
        st.markdown("### Step 2: ASC 606 Analysis")
        
        # Analyze button
        if st.session_state.extracted_data is None:
            st.info("PDF uploaded successfully! Click below to analyze the contract.")
            if st.button("Analyze Contract with AI", type="primary"):
                with st.spinner("Analyzing contract... This may take 10-20 seconds"):
                    try:
                        result = extract_and_analyze_combined(st.session_state.contract_text)
                        st.session_state.extracted_data = result['contract_info']
                        st.session_state.asc606_analysis = result['asc606_analysis']
                        logger.info("✓ Contract analysis completed successfully")
                        st.success("Analysis complete!")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Validation error: {str(e)}")
                        logger.error(f"Contract analysis validation failed: {e}")
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
                        logger.error(f"Contract analysis failed: {e}")
                        # Show helpful troubleshooting info
                        with st.expander("Troubleshooting"):
                            st.write("If analysis continues to fail, try:")
                            st.write("• Ensuring the PDF contains clear, readable text")
                            st.write("• Uploading a different PDF file")
                            st.write("• Checking your internet connection")
                            st.write("• Verifying your API key is valid")
        
        # Display results in tabs
        if st.session_state.extracted_data:
            tab1, tab2 = st.tabs(["Contract Details", "ASC 606 Analysis"])
            
            with tab1:
                data = st.session_state.extracted_data
                
                # Display in a compact format
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Customer", data.get('customer_name', 'N/A'))
                    st.metric("Start", data.get('contract_start_date', 'N/A'))
                    
                    # Handle total value with better error handling
                    total_value = data.get('total_contract_value', 0)
                    try:
                        if total_value and str(total_value).replace(',', '').replace('.', '').isdigit():
                            total_value_float = float(str(total_value).replace(',', ''))
                            st.metric("Total Value", f"${total_value_float:,.2f}")
                        else:
                            st.metric("Total Value", str(total_value) if total_value else 'N/A')
                    except (ValueError, TypeError):
                        st.metric("Total Value", str(total_value) if total_value else 'N/A')
                
                with col_b:
                    st.metric("Vendor", data.get('vendor_name', 'N/A'))
                    st.metric("End", data.get('contract_end_date', 'N/A'))
                    st.metric("Terms", data.get('payment_terms', 'N/A'))
                
                # Performance obligations
                if data.get('performance_obligations'):
                    st.markdown("**Obligations:**")
                    for i, po in enumerate(data.get('performance_obligations', []), 1):
                        st.caption(f"{i}. {po}")
            
            with tab2:
                if st.session_state.asc606_analysis:
                    analysis = st.session_state.asc606_analysis
                    
                    # Display each step - more compact
                    for step_num in range(1, 6):
                        step_key = f"step_{step_num}"
                        if step_key in analysis:
                            with st.expander(f"Step {step_num}: {analysis[step_key].get('title', '')}", expanded=False):
                                st.caption(analysis[step_key].get('description', ''))
                                if analysis[step_key].get('details'):
                                    for detail in analysis[step_key]['details']:
                                        st.caption(f"• {detail}")
                
                    # Revenue schedule
                    if 'revenue_schedule' in analysis:
                        st.markdown("---")
                        st.markdown("**Revenue Schedule**")
                        
                        schedule_df = pd.DataFrame(analysis['revenue_schedule'])
                        
                        if len(schedule_df) > 0 and 'error' not in schedule_df.columns:
                            st.dataframe(schedule_df, use_container_width=True, hide_index=True, height=200)
                            # Download CSV
                            csv_data = schedule_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="Download Revenue Schedule (CSV)",
                                data=csv_data,
                                file_name="revenue_schedule.csv",
                                mime="text/csv",
                                use_container_width=True,
                            )
                            
                            # Compact visualization
                            fig = px.bar(
                                schedule_df,
                                x='period',
                                y='revenue_amount',
                                labels={'period': 'Period', 'revenue_amount': 'Revenue ($)'}
                            )
                            fig.update_layout(
                                showlegend=False,
                                height=250,
                                margin=dict(l=0, r=0, t=20, b=0)
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Unable to generate revenue schedule")
                else:
                    st.info("Complete the contract analysis to view ASC 606 breakdown")    # Right column - Document Viewer (always visible when file is uploaded)
    with col_right:
        # Display PDF using cached function
        try:
            pdf_display = get_pdf_display_html(temp_pdf_path)
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error displaying PDF: {str(e)}")

else:
    # No file uploaded - show welcome message in left column only
    with col_left:
        # Welcome message
        st.info("Upload a SaaS contract PDF to begin analysis")
        
        # Quick info cards
        st.markdown("""
        **Step 1:** Upload your PDF contract  
        **Step 2:** AI analyzes the contract  
        **Step 3:** View ASC 606 compliance
        """)
        
        st.markdown("---")
        
        with st.expander("About ASC 606 Analysis"):
            st.markdown("""
            This tool analyzes SaaS contracts using the **ASC 606 revenue recognition framework**:
            
            **The Five-Step Model:**
            1. Identify the contract with a customer
            2. Identify performance obligations
            3. Determine the transaction price
            4. Allocate the transaction price
            5. Recognize revenue when obligations are satisfied
            
            **What you'll get:**
            - Automated contract data extraction
            - Complete ASC 606 compliance analysis
            - Revenue recognition schedule
            - Interactive visualizations
            """)

# Footer
st.markdown("---")
st.caption("ASC 606 Revenue Recognition Analyzer • Powered by Google Gemini AI")
