# Citation Fact-Checker

A Gradio-based chat interface with integrated fact-checking system for academic citations. Features a large language model (GPT-4) for chat and a smaller model (GPT-3.5) for fact-checking citations using spaCy NER and Firecrawl search.

## Features

- **Intelligent Chat**: GPT-4 powered conversational AI
- **Citation Detection**: Automatic extraction of academic citations using spaCy NER
- **Fact-Checking**: GPT-3.5 powered verification of citations with web search
- **Word-like Interface**: Review-style UI with highlighted citations and expandable comments
- **Source Verification**: Links to found sources with verification status

## Architecture

```
citation-needed/
├── app.py              # Main Gradio application
├── models/
│   ├── chat_model.py   # Model A (GPT-4) wrapper
│   ├── fact_checker.py # Model B (GPT-3.5) + DSPy signatures
│   └── ner_extractor.py # spaCy academic citation NER
├── search/
│   └── firecrawl_client.py # Firecrawl integration
├── ui/
│   ├── components.py   # Custom Gradio components
│   └── styles.css      # Word-like review styling
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### Prerequisites

- Python 3.12+
- OpenRouter API key (for GPT-4 and GPT-3.5 access)
- Firecrawl API key (for web search)

### Installation

1. **Clone and navigate to the repository:**
   ```bash
   git clone <repository-url>
   cd citation-needed
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download spaCy model:**
   ```bash
   python -m spacy download en_core_web_sm
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Running the Application

```bash
python app.py
```

The application will be available at `http://localhost:7860`

### Development

#### Code Quality
The project uses Ruff for linting and formatting:
```bash
# Check code quality
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

#### Required Environment Variables
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
```

### Running the Application

```bash
python app.py
```

The application will be available at `http://localhost:7860`

## Usage

1. **Start a conversation** by typing a message about academic topics
2. **Citations are automatically detected** in the AI's response
3. **Fact-checking happens automatically** using web search
4. **Review results** in the right panel with:
   - Highlighted citations in the text
   - Expandable comments with verification status
   - Links to found sources
   - Confidence scores

## System Components

### Model A (Chat Model)
- **Model**: GPT-4 via OpenRouter
- **Purpose**: Generate conversational responses
- **Framework**: DSPy for prompt engineering

### Model B (Fact Checker)
- **Model**: GPT-3.5-turbo via OpenRouter
- **Purpose**: Analyze and verify citations
- **Framework**: DSPy signatures for structured verification

### Citation NER
- **Engine**: spaCy with custom academic patterns
- **Detection**: Journal articles, books, DOIs, arXiv papers
- **Patterns**: Author-year format, full citations, academic URLs

### Search Integration
- **Service**: Firecrawl for web search and scraping
- **Domains**: Academic sources (PubMed, arXiv, DOI, etc.)
- **Fallback**: Mock client for testing without API keys

## Configuration

### Model Settings
```bash
# Optional: Customize models in .env
CHAT_MODEL=openai/gpt-4-turbo-preview
FACT_CHECK_MODEL=openai/gpt-3.5-turbo
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### Citation Types Supported
- Journal articles with author-year format
- Full academic citations
- DOI references
- arXiv preprints
- ISBN book references
- Academic URLs

## Development

### Testing Without API Keys
The system includes mock clients for development:
```python
# In search/firecrawl_client.py
search_client = create_search_client(use_mock=True)
```

### Adding New Citation Patterns
Extend `models/ner_extractor.py`:
```python
# Add new regex patterns to citation_patterns list
new_pattern = r'your_citation_regex_here'
self.citation_patterns.append(new_pattern)
```

### Customizing UI
Modify `ui/styles.css` for styling and `ui/components.py` for HTML generation.

## Troubleshooting

### Common Issues

1. **spaCy model not found:**
   ```bash
   python -m spacy download en_core_web_sm
   ```

2. **API key errors:**
   - Verify `.env` file exists and contains valid keys
   - Check OpenRouter account has sufficient credits

3. **Import errors:**
   - Ensure all dependencies installed: `pip install -r requirements.txt`
   - Check Python version is 3.12+

### System Status
The application shows component status on startup:
- ✓ Working correctly
- ✗ Error (check console output)

## API Keys

### OpenRouter
- Sign up at [openrouter.ai](https://openrouter.ai)
- Get API key from dashboard
- Supports GPT-4 and GPT-3.5-turbo

### Firecrawl
- Sign up at [firecrawl.dev](https://firecrawl.dev)
- Get API key from dashboard
- Used for academic source search and scraping

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.