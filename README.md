# ASC 606 Contract Analyzer

AI-powered prototype for analyzing SaaS contracts using ASC 606 revenue recognition standards.

## Features

- Upload PDF contracts
- AI-powered contract information extraction using Google Gemini
- Complete ASC 606 analysis (all 5 steps)
- Revenue recognition schedule generation
- Interactive dashboard with PDF preview

## Prerequisites

1. **Python 3.9+**
2. **Google Gemini API Key** (free from Google AI Studio)

## Setup

### 1. Get Google Gemini API Key (Free)

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Get API Key" or "Create API Key"
3. Copy your API key (you'll enter it in the app)

### 2. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 3. (Optional) Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_actual_api_key_here
```

Alternatively, you can enter your API key directly in the app when prompted.

## Running the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

1. Provide your Google Gemini API key via environment variable `GEMINI_API_KEY` or enter it in the app when prompted.
2. Upload a SaaS contract PDF (max 20MB).
3. Click "Analyze Contract with AI" to extract key terms and run the ASC 606 analysis in one step.
4. Review contract details, the 5 ASC 606 steps, and the generated revenue schedule.
5. Optionally, download the revenue schedule as CSV.

## Tech Stack

- **Frontend**: Streamlit
- **LLM**: Google Gemini 2.0 Flash (free tier)
- **PDF Processing**: pdfplumber
- **Visualization**: Plotly

## Project Structure

```
Rev_Analysis/
├── app.py                     # Main Streamlit application (single-page UI)
├── assets/
│   └── styles.css             # Custom Uber-like dark theme
├── utils/
│   ├── __init__.py            # Module exports
│   ├── pdf_extractor.py       # PDF text extraction (pdfplumber)
│   ├── llm_analyzer.py        # Gemini LLM integration with logging
│   └── asc606_engine.py       # Revenue schedule generation
├── data/
│   └── contracts/             # Uploaded PDFs (temporary, gitignored)
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git exclusions
├── ASC_606_GUIDE.md           # Comprehensive ASC 606 reference
└── README.md                  # This file
```

## Customization

### Editing LLM Prompts

The prompt for contract analysis is in `utils/llm_analyzer.py` in the `extract_and_analyze_combined()` function. You can modify the prompt string to:
- Add or remove fields
- Adjust instructions or analysis focus
- Change the JSON output structure

Restart the app after editing to use the updated prompt.

### Styling

The UI theme is in `assets/styles.css`. Customize colors, spacing, and components to match your brand.

## Google Gemini Free Tier

- **15 requests per minute** (RPM)
- **1 million tokens per minute** (TPM)
- **1,500 requests per day** (RPD)
- Perfect for prototype testing!

## License

Prototype for demonstration purposes only. Not for production use.
