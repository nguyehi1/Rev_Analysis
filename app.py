import streamlit as st
from pathlib import Path
import sys
import base64
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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



# Helper: Format currency values consistently
def _format_currency(value):
    try:
        value_float = float(str(value).replace(',', ''))
        return f"${value_float:,.2f}"
    except Exception:
        return str(value) if value not in [None, '', 0] else 'N/A'

# Helper: Initialize session state keys if missing
def _init_session_state(keys_defaults):
    for key, default in keys_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

_init_session_state({
    'contract_text': None,
    'contract_type_info': None,
    'extracted_data': None,
    'asc606_analysis': None
})

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

            # Use edited data if available, else extracted
            data = st.session_state.get('edited_contract_data') or st.session_state.extracted_data

            with tab1:
                if 'edit_mode' not in st.session_state:
                    st.session_state.edit_mode = False

                if not st.session_state.edit_mode:
                    # Display contract details (read-only)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Customer", data.get('customer_name', 'N/A'))
                        st.metric("Start", data.get('contract_start_date', 'N/A'))
                        total_value = data.get('total_contract_value', 0)
                        st.metric("Total Value", _format_currency(total_value))
                    with col_b:
                        st.metric("Vendor", data.get('vendor_name', 'N/A'))
                        st.metric("End", data.get('contract_end_date', 'N/A'))
                        st.metric("Terms", data.get('payment_terms', 'N/A'))

                    if data.get('performance_obligations'):
                        st.markdown("**Obligations:**")
                        for i, po in enumerate(data.get('performance_obligations', []), 1):
                            st.caption(f"{i}. {po}")

                    obligations = data.get('obligations')
                    if obligations and isinstance(obligations, list) and len(obligations) > 0:
                        st.markdown("**Obligation Allocations:**")
                        obligations_table = []
                        for idx, ob in enumerate(obligations, 1):
                            name = ob.get('name', 'N/A')
                            desc = ob.get('description', '')
                            value = ob.get('allocated_value', 0)
                            value_str = _format_currency(value)
                            obligations_table.append((str(idx), name, desc, value_str))
                        table_html = """
                        <style>
                        .obligation-table {
                            width: 100%;
                            border-collapse: collapse;
                            font-size: 14px;
                            color: #c9d1d9;
                            background: none;
                        }
                        .obligation-table th, .obligation-table td {
                            border: 0.5px solid #363636;
                            padding: 3px 6px;
                            text-align: left;
                            background: none;
                            color: #c9d1d9;
                        }
                        .obligation-table th {
                            background: #121821;
                            font-weight: 600;
                            color: #c9d1d9;
                        }
                        </style>
                        <table class="obligation-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Obligation</th>
                                    <th>Description</th>
                                    <th>Allocated Value</th>
                                </tr>
                            </thead>
                            <tbody>
                        """
                        for row in obligations_table:
                            table_html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>"
                        table_html += "</tbody></table>"
                        st.markdown(table_html, unsafe_allow_html=True)

                    # Edit button
                    if st.button("Edit Details", key="edit_details_btn"):
                        st.session_state.edit_mode = True
                        st.session_state.edited_contract_data = data.copy()
                        st.rerun()

                else:
                    # Edit mode: show input fields
                    edited = st.session_state.get('edited_contract_data', {}).copy()
                    col_a, col_b = st.columns(2)
                    with col_a:
                        edited['customer_name'] = st.text_input("Customer", value=edited.get('customer_name', ''))
                        edited['contract_start_date'] = st.text_input("Start Date (YYYY-MM-DD)", value=edited.get('contract_start_date', ''))
                        edited['total_contract_value'] = st.text_input("Total Value", value=str(edited.get('total_contract_value', '')))
                    with col_b:
                        edited['vendor_name'] = st.text_input("Vendor", value=edited.get('vendor_name', ''))
                        edited['contract_end_date'] = st.text_input("End Date (YYYY-MM-DD)", value=edited.get('contract_end_date', ''))
                        edited['payment_terms'] = st.text_input("Terms", value=edited.get('payment_terms', ''))

                    # Obligations (simple editable list)
                    st.markdown("**Obligations (comma separated):**")
                    perf_ob_str = ', '.join(edited.get('performance_obligations', [])) if isinstance(edited.get('performance_obligations', []), list) else ''
                    perf_ob_str = st.text_input("Performance Obligations", value=perf_ob_str)
                    edited['performance_obligations'] = [s.strip() for s in perf_ob_str.split(',')] if perf_ob_str else []

                    # Obligations with allocated value (simple table)
                    obligations = edited.get('obligations', [])
                    st.markdown("**Obligation Allocations:** (edit below)")
                    new_obligations = []
                    for idx, ob in enumerate(obligations, 1):
                        # Use equal width columns for consistency
                        cols = st.columns(4)
                        name = cols[0].text_input(f"Obligation Name {idx}", value=ob.get('name', ''), key=f"ob_name_{idx}")
                        desc = cols[1].text_input(f"Description {idx}", value=ob.get('description', ''), key=f"ob_desc_{idx}")
                        value = cols[2].text_input(f"Allocated Value {idx}", value=str(ob.get('allocated_value', '')), key=f"ob_val_{idx}")
                        # Helper: Format currency values consistently
                        def _format_currency(value):
                            try:
                                value_float = float(str(value).replace(',', ''))
                                return f"${value_float:,.2f}"
                            except Exception:
                                return str(value) if value not in [None, '', 0] else 'N/A'
                        # Add a blank column for spacing/alignment if needed
                        _ = cols[3].markdown("")
                        new_obligations.append({'name': name, 'description': desc, 'allocated_value': value})
                    edited['obligations'] = new_obligations

                    # Save and re-run analysis button, plus cancel
                    run_col, cancel_col = st.columns([2,1])
                    # Ensure consistent button width with custom CSS
                    st.markdown("""
                        <style>
                        .stButton > button#save_rerun_btn {
                            min-width: 220px;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    with run_col:
                        if st.button("Save and re-run analysis", key="save_rerun_btn", type="primary"):
                            st.session_state.edited_contract_data = edited
                            st.session_state.edit_mode = False
                            st.session_state.extracted_data = edited
                            st.session_state.asc606_analysis = None
                            import json
                            try:
                                result = extract_and_analyze_combined(json.dumps(edited))
                                st.session_state.extracted_data = result['contract_info']
                                st.session_state.asc606_analysis = result['asc606_analysis']
                                st.success("Analysis complete with edited details!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Analysis failed: {str(e)}")
                    with cancel_col:
                        if st.button("Cancel", key="cancel_edit_btn"):
                            st.session_state.edit_mode = False
                            st.rerun()
            
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
                            # Identify obligation-specific columns
                            obligation_cols = [col for col in schedule_df.columns if col.startswith('revenue_') and col != 'revenue_amount']
                            
                            # Show multi-obligation summary if applicable
                            if obligation_cols:
                                st.info(f"📊 Multi-obligation contract with {len(obligation_cols)} performance obligations")
                            
                            # Reorder columns for better display
                            base_cols = ['period', 'period_start', 'period_end']
                            display_cols = base_cols + obligation_cols + ['revenue_amount', 'deferred_revenue']
                            # Keep only columns that exist
                            display_cols = [col for col in display_cols if col in schedule_df.columns]
                            # Add any remaining columns not already included
                            remaining_cols = [col for col in schedule_df.columns if col not in display_cols]
                            display_cols.extend(remaining_cols)
                            
                            display_df = schedule_df[display_cols].copy()
                            
                            # Format currency columns for display
                            currency_cols = ['revenue_amount', 'deferred_revenue'] + obligation_cols
                            for col in currency_cols:
                                if col in display_df.columns:
                                    display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if isinstance(x, (int, float)) else x)
                            
                            # Configure column display settings to ensure all columns are visible
                            column_config = {}
                            for col in display_df.columns:
                                if col.startswith('revenue_'):
                                    # Make revenue columns more prominent
                                    column_config[col] = st.column_config.TextColumn(
                                        col.replace('revenue_', '').replace('_', ' ').title(),
                                        width="medium",
                                        help=f"Revenue for {col.replace('revenue_', '')}"
                                    )
                                elif col == 'deferred_revenue':
                                    column_config[col] = st.column_config.TextColumn(
                                        "Deferred Revenue",
                                        width="medium"
                                    )
                            
                            # Display the dataframe with all columns and custom config
                            st.dataframe(
                                display_df,
                                use_container_width=True,
                                hide_index=True,
                                height=min(400, len(display_df) * 35 + 38),
                                column_config=column_config
                            )
                            
                            # Download CSV with raw numbers
                            csv_data = schedule_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download Revenue Schedule (CSV)",
                                data=csv_data,
                                file_name="revenue_schedule.csv",
                                mime="text/csv",
                                use_container_width=True,
                            )
                            
                            # Enhanced visualization
                            st.markdown("**Revenue Visualization**")
                            
                            # Let user choose what to visualize
                            viz_type = st.radio(
                                "Visualization type:",
                                ["Stacked", "Grouped", "Line Chart"],
                                horizontal=True,
                                help="Choose how to display revenue data"
                            )
                            
                            # Column selection for visualization
                            all_revenue_cols = obligation_cols + ['revenue_amount']
                            default_cols = ['revenue_amount'] if 'revenue_amount' in all_revenue_cols else obligation_cols[:1]
                            
                            selected_cols = st.multiselect(
                                "Select revenue columns to visualize:",
                                all_revenue_cols,
                                default=default_cols if obligation_cols else ['revenue_amount']
                            )
                            
                            if selected_cols:
                                # Create visualization based on type
                                if viz_type == "Stacked":
                                    fig = px.bar(
                                        schedule_df,
                                        x='period',
                                        y=selected_cols,
                                        labels={'period': 'Period', 'value': 'Revenue', 'variable': 'Obligation'},
                                        title="Revenue Recognition by Period"
                                    )
                                    fig.update_layout(
                                        barmode='stack',
                                        height=400,
                                        margin=dict(l=0, r=0, t=40, b=0),
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                    )
                                    
                                elif viz_type == "Grouped":
                                    fig = px.bar(
                                        schedule_df,
                                        x='period',
                                        y=selected_cols,
                                        labels={'period': 'Period', 'value': 'Revenue', 'variable': 'Obligation'},
                                        title="Revenue Recognition by Period"
                                    )
                                    fig.update_layout(
                                        barmode='group',
                                        height=400,
                                        margin=dict(l=0, r=0, t=40, b=0),
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                                    )
                                    
                                else:  # Line Chart
                                    fig = go.Figure()
                                    for col in selected_cols:
                                        fig.add_trace(go.Scatter(
                                            x=schedule_df['period'],
                                            y=schedule_df[col],
                                            mode='lines+markers',
                                            name=col.replace('revenue_', '').replace('_', ' ').title(),
                                            line=dict(width=3),
                                            marker=dict(size=8)
                                        ))
                                    
                                    fig.update_layout(
                                        title="Revenue Recognition Trend",
                                        xaxis_title="Period",
                                        yaxis_title="Revenue",
                                        height=400,
                                        margin=dict(l=0, r=0, t=40, b=0),
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                        hovermode='x unified'
                                    )
                                
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Add deferred revenue chart if available
                                if 'deferred_revenue' in schedule_df.columns:
                                    with st.expander("View Deferred Revenue", expanded=False):
                                        fig_deferred = go.Figure()
                                        fig_deferred.add_trace(go.Scatter(
                                            x=schedule_df['period'],
                                            y=schedule_df['deferred_revenue'],
                                            mode='lines+markers',
                                            name='Deferred Revenue',
                                            fill='tozeroy',
                                            line=dict(color='#FF6B6B', width=3),
                                            marker=dict(size=8)
                                        ))
                                        
                                        fig_deferred.update_layout(
                                            title="Deferred Revenue Over Time",
                                            xaxis_title="Period",
                                            yaxis_title="Deferred Revenue",
                                            height=300,
                                            margin=dict(l=0, r=0, t=40, b=0),
                                            hovermode='x unified'
                                        )
                                        
                                        st.plotly_chart(fig_deferred, use_container_width=True)
                        else:
                            st.warning("Unable to generate revenue schedule")
                else:
                    st.info("Complete the contract analysis to view ASC 606 breakdown")
    
    # Right column - Document Viewer (always visible when file is uploaded)
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
            - Revenue recognition schedule with multi-obligation support
            - Interactive visualizations
            """)

# Footer
st.markdown("---")
st.caption("ASC 606 Revenue Recognition Analyzer • Powered by Google Gemini AI")