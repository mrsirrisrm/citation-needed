"""
FastAPI Backend Server for Citation Needed

This module provides a REST API backend for the citation fact-checking system,
separating the core functionality from the UI layer.
"""

import os
import time
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our components
from models.chat_model import create_chat_model
from models.fact_checker import create_fact_checker
from models.ner_extractor import create_ner_extractor
from search.firecrawl_client import create_search_client
from async_processor import TaskStatus, async_processor, create_async_task_id

# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    response: str
    citations: List[Dict[str, Any]]
    task_id: Optional[str] = None

class FactCheckRequest(BaseModel):
    citations: List[Dict[str, Any]]

class TaskStatusResponse(BaseModel):
    status: str
    progress: float
    completed: bool
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    has_partial: bool = False

class SystemStatusResponse(BaseModel):
    chat_model: bool
    search_client: bool
    ner_extractor: bool
    fact_checker: bool
    search_backend: str
    active_tasks: int

class UsageStatsResponse(BaseModel):
    total_calls: int
    total_cost_usd: float
    successful_calls: int
    total_tokens: int
    success_rate: float
    avg_duration: float
    provider_breakdown: Optional[Dict[str, Any]] = None
    top_endpoints: Optional[List[Dict[str, Any]]] = None

# Initialize FastAPI app
app = FastAPI(
    title="Citation Needed API",
    description="Backend API for citation fact-checking system",
    version="1.0.0"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global application instance
class CitationAPI:
    """Main API application class"""

    def __init__(self):
        """Initialize all components"""
        self.search_client = None
        self.chat_model = None
        self.ner_extractor = None
        self.fact_checker = None
        self.pending_tasks = {}

        self._initialize_components()

    def _initialize_components(self):
        """Initialize all components with error handling"""
        try:
            print("Initializing search client...")
            searxng_url = os.getenv("SEARXNG_URL")
            use_searxng = bool(searxng_url)

            if use_searxng:
                print(f"Using SearXNG at: {searxng_url}")
            else:
                print("Using Firecrawl (external API)")

            self.search_client = create_search_client(use_searxng=use_searxng)

            if self.search_client.validate_setup():
                client_type = "SearXNG" if use_searxng else "Firecrawl"
                print(f"✓ Search client ({client_type}): OK")
            else:
                print("✗ Search client validation failed")

        except Exception as e:
            print(f"Search client error: {e}")
            try:
                self.search_client = create_search_client(use_mock=True)
                print("✓ Fallback to mock search client")
            except Exception as e2:
                print(f"Mock client fallback failed: {e2}")

        try:
            print("Initializing chat model...")
            self.chat_model = create_chat_model()
            print(f"Chat model: {'✓' if self.chat_model.validate_setup() else '✗'}")
        except Exception as e:
            print(f"Chat model error: {e}")

        try:
            print("Initializing NER extractor...")
            self.ner_extractor = create_ner_extractor()
            print(f"NER extractor: {'✓' if self.ner_extractor.validate_setup() else '✗'}")
        except Exception as e:
            print(f"NER extractor error: {e}")

        try:
            print("Initializing fact checker...")
            self.fact_checker = create_fact_checker(self.search_client)
            print(f"Fact checker: {'✓' if self.fact_checker.validate_setup() else '✗'}")
        except Exception as e:
            print(f"Fact checker error: {e}")

    def process_message(self, message: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process a chat message and return response with fact-checking info"""
        # Generate chat response
        if self.chat_model:
            try:
                # Convert history format for chat model
                converted_history = []
                if history:
                    for msg in history:
                        if msg.get("role") == "user":
                            user_content = msg.get("content", "")
                        elif msg.get("role") == "assistant" and user_content:
                            assistant_content = msg.get("content", "")
                            converted_history.append([user_content, assistant_content])
                            user_content = None

                response = self.chat_model.chat(message, converted_history)
            except Exception as e:
                response = f"Error generating response: {str(e)}"
        else:
            response = "Chat model not available. Please check your configuration."

        # Extract citations from response
        citations = []
        if self.ner_extractor:
            try:
                extracted_citations = self.ner_extractor.extract_citations(response)
                print(f"Found {len(extracted_citations)} citations")

                # Convert citations to dict format
                for citation in extracted_citations:
                    citations.append({
                        "text": citation.text,
                        "start": citation.start,
                        "end": citation.end,
                        "type": citation.type,
                        "confidence": citation.confidence
                    })
            except Exception as e:
                print(f"Citation extraction error: {e}")

        # Start async fact-checking if citations found
        task_id = None
        if citations and self.fact_checker:
            try:
                print(f"🚀 Starting async fact-checking for {len(citations)} citations")
                task_id = create_async_task_id()

                self.pending_tasks[task_id] = {
                    'response': response,
                    'citations': citations
                }

                # Register callback for task completion
                async_processor.register_callback(task_id, self._on_fact_check_complete)
                async_processor.register_progress_callback(task_id, self._on_fact_check_progress)

                # Create wrapper function with progress callback
                def fact_check_with_progress(citations_list):
                    # Convert dict citations back to citation objects
                    from models.ner_extractor import Citation
                    citation_objects = []
                    for cit_dict in citations_list:
                        citation = Citation(
                            text=cit_dict['text'],
                            start=cit_dict['start'],
                            end=cit_dict['end'],
                            type=cit_dict['type'],
                            confidence=cit_dict['confidence']
                        )
                        citation_objects.append(citation)

                    return self.fact_checker.fact_check_citations(
                        citation_objects,
                        progress_callback=lambda progress, result: async_processor.update_progress(task_id, progress, result)
                    )

                # Start async fact-checking
                async_processor.create_task(
                    task_id,
                    fact_check_with_progress,
                    citations,
                    timeout=45.0
                )

                print(f"Started async fact-checking task: {task_id}")

            except Exception as e:
                print(f"Failed to start async fact-checking: {e}")

        return {
            "response": response,
            "citations": citations,
            "task_id": task_id
        }

    def _on_fact_check_progress(self, task_id: str, progress: float, partial_result=None):
        """Callback when async fact-checking progress updates"""
        print(f"🔄 Progress update for task {task_id}: {progress:.1%}")

        if partial_result and task_id in self.pending_tasks:
            task_data = self.pending_tasks[task_id]
            if 'partial_results' not in task_data:
                task_data['partial_results'] = []

            task_data['partial_results'].append(partial_result)

    def _on_fact_check_complete(self, task_id: str, fact_check_results: list = None, error: str = None):
        """Callback when async fact-checking completes"""
        print(f"Async fact-checking completed for task {task_id}")

        if error:
            print(f"Fact-checking error: {error}")
            return

        if fact_check_results and task_id in self.pending_tasks:
            task_data = self.pending_tasks[task_id]
            try:
                # Convert fact check results to dict format
                results_dict = []
                for result in fact_check_results:
                    result_dict = {
                        "citation": {
                            "text": result.citation.text,
                            "start": result.citation.start,
                            "end": result.citation.end,
                            "type": result.citation.type,
                            "confidence": result.citation.confidence
                        },
                        "verification_status": result.verification_status,
                        "explanation": result.explanation,
                        "confidence": result.confidence,
                        "sources_found": result.sources_found
                    }
                    results_dict.append(result_dict)

                # Store the updated result for API response
                task_data['fact_check_results'] = results_dict
                task_data['completed'] = True

                print(f"Fact-checking results ready for task {task_id}")

            except Exception as e:
                print(f"Error formatting async fact-check results: {e}")

    
    
    def get_task_status(self, task_id: str) -> dict:
        """Get status of an async task"""
        if task_id not in self.pending_tasks:
            return {'status': 'not_found'}

        task = async_processor.get_task(task_id)
        if not task:
            return {'status': 'not_found'}

        response = {
            'status': task.status.value,
            'progress': task.progress,
            'error': task.error,
            'completed': task.status == TaskStatus.COMPLETED
        }

        # Include partial results if available
        task_data = self.pending_tasks.get(task_id, {})
        partial_results = task_data.get('partial_results', [])

        response['has_partial'] = len(partial_results) > 0

        # Include final result if completed
        if task.status == TaskStatus.COMPLETED and 'fact_check_results' in task_data:
            response['result'] = {
                'fact_check_results': task_data['fact_check_results']
            }

        return response

    def get_system_status(self) -> dict:
        """Get system status information"""
        # Determine search backend
        search_backend = "Firecrawl"
        if hasattr(self.search_client, '__class__'):
            if "SearXNG" in str(type(self.search_client)):
                search_backend = "SearXNG (Local)"
            elif "Mock" in str(type(self.search_client)):
                search_backend = "Mock (Testing)"

        # Safe validation checks
        chat_model_ok = bool(self.chat_model and hasattr(self.chat_model, 'validate_setup') and self.chat_model.validate_setup())
        search_client_ok = bool(self.search_client and hasattr(self.search_client, 'validate_setup') and self.search_client.validate_setup())
        ner_extractor_ok = bool(self.ner_extractor and hasattr(self.ner_extractor, 'validate_setup') and self.ner_extractor.validate_setup())
        fact_checker_ok = bool(self.fact_checker and hasattr(self.fact_checker, 'validate_setup') and self.fact_checker.validate_setup())

        return {
            "chat_model": chat_model_ok,
            "search_client": search_client_ok,
            "ner_extractor": ner_extractor_ok,
            "fact_checker": fact_checker_ok,
            "search_backend": search_backend,
            "active_tasks": len(self.pending_tasks)
        }

    def get_usage_stats(self) -> dict:
        """Get usage statistics"""
        try:
            from usage_tracker import usage_tracker
            daily_stats = usage_tracker.get_daily_stats()

            return {
                "total_calls": daily_stats.total_calls,
                "total_cost_usd": daily_stats.total_cost_usd,
                "successful_calls": daily_stats.successful_calls,
                "total_tokens": daily_stats.total_tokens,
                "success_rate": daily_stats.successful_calls / max(1, daily_stats.total_calls) * 100,
                "avg_duration": daily_stats.average_duration,
                "provider_breakdown": daily_stats.provider_breakdown,
                "top_endpoints": daily_stats.top_endpoints[:5] if daily_stats.top_endpoints else []
            }
        except Exception as e:
            print(f"Error getting usage stats: {e}")
            return {
                "total_calls": 0,
                "total_cost_usd": 0.0,
                "successful_calls": 0,
                "total_tokens": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "provider_breakdown": None,
                "top_endpoints": []
            }

# Initialize API instance
api_instance = CitationAPI()

# API Endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return response with fact-checking info"""
    try:
        result = api_instance.process_message(request.message, request.history)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get status of an async fact-checking task"""
    try:
        status = api_instance.get_task_status(task_id)
        if status['status'] == 'not_found':
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskStatusResponse(**status)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get system status information"""
    try:
        status = api_instance.get_system_status()
        return SystemStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/stats", response_model=UsageStatsResponse)
async def get_usage_stats():
    """Get usage statistics"""
    try:
        stats = api_instance.get_usage_stats()
        return UsageStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)