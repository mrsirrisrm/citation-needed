# Citation Fact-Checking System - Project Plan

## Overview
Building a Gradio-based chat interface with integrated fact-checking system. Model A (GPT-4) handles chat, Model B (GPT-3.5) fact-checks academic citations using spaCy NER and Firecrawl search.

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

## Implementation Checklist

### Phase 1: Core Infrastructure
- [x] Set up Python environment and requirements.txt
- [x] Create .env.example configuration file
- [x] Create project directory structure

### Phase 2: Model Integration
- [x] Implement basic Gradio chat interface
- [x] Create Model A (GPT-4) chat wrapper with DSPy
- [x] Build spaCy pipeline for academic citation NER
- [x] Implement Model B fact-checker with DSPy signatures
- [x] Integrate Firecrawl for source searching

### Phase 3: UI Enhancement
- [x] Design Word-like review interface with highlighted text
- [x] Implement expandable comment system with source links
- [x] Add verification status display

### Phase 4: Integration & Testing
- [x] Connect all components in main Gradio app
- [x] Test end-to-end workflow and add error handling
- [x] Polish UI and user experience

## Technical Stack
- **Python**: 3.12
- **Frontend**: Gradio with custom CSS
- **LLM Framework**: DSPy
- **Models**: OpenAI GPT-4 (chat) + GPT-3.5-turbo (fact-check)
- **NER**: spaCy for academic citation detection
- **Search**: Firecrawl for web search and verification
- **API**: OpenRouter for model access

## Key Features
- [x] Real-time chat with GPT-4
- [x] Automatic academic citation detection
- [x] Source verification with search results
- [x] Word-like review interface with comments
- [x] Expandable verification details
- [x] Error handling and edge cases

## Project Status: ✅ COMPLETE

All phases have been successfully implemented:

1. **Core Infrastructure** - Complete with requirements, environment setup, and project structure
2. **Model Integration** - Complete with DSPy-based GPT-4 chat and GPT-3.5 fact-checking
3. **UI Enhancement** - Complete with Word-like review interface and interactive citations
4. **Integration & Testing** - Complete with full end-to-end workflow

### Ready to Use
- Set up environment variables in `.env`
- Install dependencies: `pip install -r requirements.txt`
- Download spaCy model: `python -m spacy download en_core_web_sm`
- Run: `python app.py`

The system provides real-time fact-checking of academic citations with a Microsoft Word-like review interface.