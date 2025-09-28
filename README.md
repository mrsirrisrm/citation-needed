# Citation Needed

A React + FastAPI chat interface with integrated fact-checking system for academic citations. Features a large language model (GPT-4) for chat and a smaller model (GPT-3.5) for fact-checking citations using spaCy NER and web search.

## Features

- **Modern React Frontend**: Sleek, responsive UI with vibrant color scheme and smooth animations
- **Intelligent Chat**: GPT-4 powered conversational AI with real-time message streaming
- **Citation Detection**: Automatic extraction of academic citations using spaCy NER
- **Fact-Checking**: GPT-3.5 powered verification of citations with web search
- **Asynchronous Processing**: Non-blocking fact-checking with real-time progress updates
- **Word-like Interface**: Review-style UI with highlighted citations and expandable comments
- **Source Verification**: Links to found sources with verification status
- **Usage Analytics**: Track API usage and system performance metrics
- **Hallucination Detection**: Advanced testing for AI response reliability
- **Type Safety**: Full TypeScript support with comprehensive type checking

## Architecture

```
citation-needed/
├── backend_server.py        # FastAPI backend server
├── async_processor.py       # Asynchronous task processing
├── usage_tracker.py         # API usage and analytics
├── models/
│   ├── chat_model.py        # Model A (GPT-4) wrapper
│   ├── fact_checker.py      # Model B (GPT-3.5) + DSPy signatures
│   ├── ner_extractor.py     # spaCy academic citation NER
│   ├── citation_parser.py   # Citation parsing utilities
│   └── types.py             # Type definitions
├── search/
│   ├── firecrawl_client.py  # Firecrawl integration
│   └── searxng_client.py    # SearXNG search integration
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React application
│   │   ├── components/      # React components
│   │   │   ├── Chat.tsx     # Chat interface
│   │   │   ├── FactCheckPanel.tsx # Fact-checking results
│   │   │   ├── SystemStatus.tsx   # System status display
│   │   │   └── UsageStatsPanel.tsx # Usage analytics
│   │   └── index.css        # Modern styling with Tailwind
│   ├── package.json
│   └── vite.config.ts       # Vite build configuration
├── tests/                   # Comprehensive test suite
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### Prerequisites

#### For Docker Setup (Recommended)
- Docker and Docker Compose
- OpenRouter API key (for GPT-4 and GPT-3.5 access)

#### For Manual Setup
- Python 3.12+
- Node.js 18+ and npm (for React frontend)
- OpenRouter API key (for GPT-4 and GPT-3.5 access)
- **Search service** (choose one):
  - SearXNG instance URL (self-hosted, privacy-focused), OR
  - Firecrawl API key (cloud service)

### Installation

Choose between Docker (recommended for quick setup) or manual installation:

#### Option A: Docker Setup (Recommended)

1. **Clone and navigate to the repository:**
   ```bash
   git clone <repository-url>
   cd citation-needed
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.docker .env
   # Edit .env with your OpenRouter API key
   ```

3. **Start the application:**
   ```bash
   # Start backend + SearXNG
   docker-compose up -d

   # Or start with frontend dev server too
   docker-compose --profile frontend up -d
   ```

   The application will be available at:
   - Backend API: `http://localhost:8000`
   - SearXNG: `http://localhost:8080`
   - Frontend (if using profile): `http://localhost:5173`

#### Option B: Manual Installation

1. **Clone and navigate to the repository:**
   ```bash
   git clone <repository-url>
   cd citation-needed
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Download spaCy model:**
   ```bash
   python -m spacy download en_core_web_sm
   ```

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Running the Application

#### Docker (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### Manual Development Mode
```bash
# Terminal 1: Start the FastAPI backend
python backend_server.py

# Terminal 2: Start the React frontend
cd frontend
npm run dev
```

**Access URLs:**
- Backend API: `http://localhost:8000`
- Frontend (dev mode): `http://localhost:5173`
- SearXNG (if using Docker): `http://localhost:8080`

### Development

#### Code Quality
The project uses Ruff for Python linting and formatting, plus ESLint for TypeScript:
```bash
# Python code quality
ruff check .          # Check issues
ruff check --fix .    # Auto-fix issues
ruff format .         # Format code

# Frontend code quality
cd frontend
npm run lint          # Check TypeScript/React issues
npm run build         # Type-check and build
```

#### Testing
Run the comprehensive test suite:
```bash
# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py ner           # NER extraction tests
python run_tests.py fact_checker  # Fact-checking tests
python run_tests.py integration   # Integration tests

# Run individual test files
python test_hallucination.py      # Hallucination detection
python test_usage_tracking.py     # Usage analytics
```

#### Environment Variables

##### Required
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

##### Search Configuration (Choose One)
```bash
# Option 1: Use SearXNG (privacy-focused, self-hosted)
SEARXNG_URL=http://localhost:8080

# Option 2: Use Firecrawl (cloud service)
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
```

**Search Priority**: If `SEARXNG_URL` is set, it will be used for web search. Otherwise, the system falls back to Firecrawl. If neither is configured, a mock search client is used for development.

## Usage

1. **Open the application** in your browser (usually `http://localhost:5173` for development)
2. **Start a conversation** by typing a message about academic topics in the chat interface
3. **Citations are automatically detected** in the AI's response using spaCy NER
4. **Fact-checking happens asynchronously** with real-time progress updates
5. **Review results** in the dedicated panels:
   - **Chat Tab**: View conversation history with highlighted citations
   - **Fact-Check Tab**: Detailed verification results with source links
   - **Usage Tab**: API usage statistics and performance metrics
   - **Status Tab**: System component health and version information

## System Components

### Frontend (React + TypeScript)
- **Framework**: React 18 with TypeScript and Vite
- **Styling**: Tailwind CSS with modern gradient design
- **Components**: Modular chat, fact-checking, and analytics panels
- **Features**: Real-time updates, responsive design, accessibility support

### Backend (FastAPI)
- **Framework**: FastAPI with asynchronous processing
- **API**: RESTful endpoints with automatic OpenAPI documentation
- **Processing**: Background task management for non-blocking operations
- **Analytics**: Built-in usage tracking and performance monitoring

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
- **Primary**: Firecrawl for web search and scraping
- **Alternative**: SearXNG integration for privacy-focused search
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
- **React Components**: Modify files in `frontend/src/components/`
- **Styling**: Update `frontend/src/index.css` and Tailwind configuration
- **Build Configuration**: Adjust `frontend/vite.config.ts` and `frontend/tsconfig.json`

### API Documentation
When running the backend, visit `http://localhost:8000/docs` for interactive API documentation powered by FastAPI and OpenAPI.

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

4. **Frontend build issues:**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

5. **CORS errors:**
   - Backend automatically configures CORS for frontend
   - Check that backend is running on port 8000
   - Verify frontend is accessing the correct backend URL

6. **Docker issues:**
   ```bash
   # Rebuild containers after code changes
   docker-compose build --no-cache

   # Check container logs
   docker-compose logs citation-needed
   docker-compose logs searxng

   # Restart services
   docker-compose restart
   ```

### System Status
- **Real-time monitoring**: Check the Status tab in the frontend
- **API health**: Visit `http://localhost:8000/health` for backend status
- **Component status**: ✓ Working correctly, ✗ Error (check console output)
- **Usage metrics**: Available in the Usage tab with detailed analytics

## Search Setup

### Docker Setup (Automatic)

When using Docker Compose, SearXNG is **automatically included** and configured:
- No additional setup required
- SearXNG runs on `http://localhost:8080`
- Privacy-focused search with no API limits
- Automatically connected to the Citation Needed backend

### Manual Setup Options

#### Option 1: SearXNG (Recommended for Privacy)

For manual installation, you can set up SearXNG separately:

```bash
# Quick setup with Docker
docker run -d \
  --name searxng \
  -p 8080:8080 \
  searxng/searxng

# Then set in .env:
# SEARXNG_URL=http://localhost:8080
```

**Benefits:**
- Privacy-focused (no tracking)
- Self-hosted (full control)
- No API limits or costs
- Aggregates results from multiple search engines

#### Option 2: Firecrawl (Cloud Service)

- Sign up at [firecrawl.dev](https://firecrawl.dev)
- Get API key from dashboard
- Used for academic source search and scraping
- Set `FIRECRAWL_API_KEY` in your `.env` file

## API Keys

### OpenRouter
- Sign up at [openrouter.ai](https://openrouter.ai)
- Get API key from dashboard
- Supports GPT-4 and GPT-3.5-turbo

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.