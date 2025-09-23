import os

import gradio as gr
from dotenv import load_dotenv

from async_processor import TaskStatus, async_processor, create_async_task_id

# Import our components
from models.chat_model import create_chat_model
from models.fact_checker import create_fact_checker
from models.ner_extractor import create_ner_extractor
from search.firecrawl_client import create_search_client
from ui.components import format_message_with_citations


# Load environment variables
load_dotenv()

# Add Flask for async task status endpoints
import threading

from flask import Flask, jsonify


# Create Flask app for async endpoints
flask_app = Flask(__name__)

# Add CORS headers for development
@flask_app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@flask_app.route('/task_status/<task_id>')
def get_task_status(task_id):
    """Get status of an async task"""
    try:
        status = app.get_task_status(task_id)
        if status['status'] == 'not_found':
            return jsonify({'error': 'Task not found'}), 404

        result = app.get_task_result(task_id)

        # Check for partial results
        task_data = app.pending_tasks.get(task_id, {})
        partial_panel = task_data.get('partial_panel')

        response = {
            'status': status['status'],
            'completed': status['completed'],
            'progress': status['progress'],
            'error': status['error'],
            'result': result
        }

        # Include partial results if available
        if partial_panel:
            response['partial_panel'] = partial_panel
            response['has_partial'] = True
        else:
            response['has_partial'] = False

        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_flask_server():
    """Run Flask server in a separate thread"""
    flask_app.run(host='127.0.0.1', port=5001, debug=False)

# Start Flask server in background thread
flask_thread = threading.Thread(target=run_flask_server, daemon=True)
flask_thread.start()


class CitationFactChecker:
    """Main application class that coordinates all components"""

    def __init__(self):
        """Initialize all components"""
        self.search_client = None
        self.chat_model = None
        self.ner_extractor = None
        self.fact_checker = None
        self.pending_tasks = {}  # Store task IDs for async operations

        self._initialize_components()

    def _initialize_components(self):
        """Initialize all components with error handling"""
        try:
            print("Initializing search client...")
            # Check if SearXNG URL is configured
            searxng_url = os.getenv("SEARXNG_URL")
            use_searxng = bool(searxng_url)

            if use_searxng:
                print(f"Using SearXNG at: {searxng_url}")
            else:
                print("Using Firecrawl (external API)")

            self.search_client = create_search_client(use_searxng=use_searxng)

            # Validate the client
            if self.search_client.validate_setup():
                client_type = "SearXNG" if use_searxng else "Firecrawl"
                print(f"✓ Search client ({client_type}): OK")
            else:
                print("✗ Search client validation failed")

        except Exception as e:
            print(f"Search client error: {e}")
            # Fall back to mock client
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

    def process_message(self, message: str, history: list[list[str]]) -> tuple[str, str, str]:
        """
        Process a chat message and return response with fact-checking

        Args:
            message: User message
            history: Chat history

        Returns:
            Tuple of (chat_response, fact_check_panel_html, task_id)
        """
        # Step 1: Generate chat response
        if self.chat_model:
            try:
                response = self.chat_model.chat(message, history)
            except Exception as e:
                response = f"Error generating response: {str(e)}"
        else:
            response = "Chat model not available. Please check your configuration."

        # Step 2: Extract citations from response
        citations = []
        if self.ner_extractor:
            try:
                citations = self.ner_extractor.extract_citations(response)
                print(f"Found {len(citations)} citations")
            except Exception as e:
                print(f"Citation extraction error: {e}")

        # Step 3: Create initial response without fact-checking
        try:
            formatted_response, initial_fact_check_panel = format_message_with_citations(
                response, []
            )
        except Exception as e:
            formatted_response = response
            initial_fact_check_panel = f"<p>Error formatting results: {str(e)}</p>"

        # Step 4: Start async fact-checking if citations found
        task_id = None
        print(f"🔍 Citations found: {len(citations)}, Fact checker available: {self.fact_checker is not None}")

        if citations and self.fact_checker:
            try:
                print(f"🚀 Starting async fact-checking for {len(citations)} citations")
                task_id = create_async_task_id()
                print(f"🆔 Generated task ID: {task_id}")
                self.pending_tasks[task_id] = {
                    'response': response,
                    'citations': citations,
                    'formatted_response': formatted_response
                }

                # Register callback for task completion
                async_processor.register_callback(task_id, self._on_fact_check_complete)

                # Register progress callback for real-time updates
                async_processor.register_progress_callback(task_id, self._on_fact_check_progress)

                # Create wrapper function with progress callback
                def fact_check_with_progress(citations_list):
                    return self.fact_checker.fact_check_citations(
                        citations_list,
                        progress_callback=lambda progress, result: async_processor.update_progress(task_id, progress, result)
                    )

                # Start async fact-checking
                async_processor.create_task(
                    task_id,
                    fact_check_with_progress,
                    citations,
                    timeout=45.0  # 45 second timeout for fact-checking
                )

                print(f"Started async fact-checking task: {task_id}")

            except Exception as e:
                print(f"Failed to start async fact-checking: {e}")
                # Fall back to synchronous processing
                try:
                    fact_check_results = self.fact_checker.fact_check_citations(citations)
                    formatted_response, fact_check_panel = format_message_with_citations(
                        response, fact_check_results
                    )
                    return formatted_response, fact_check_panel, None
                except Exception as e2:
                    print(f"Synchronous fallback also failed: {e2}")
                    return formatted_response, initial_fact_check_panel, None

        return formatted_response, initial_fact_check_panel, task_id

    def _on_fact_check_progress(self, task_id: str, progress: float, partial_result=None):
        """Callback when async fact-checking progress updates"""
        print(f"🔄 Progress update for task {task_id}: {progress:.1%}")

        if partial_result and task_id in self.pending_tasks:
            # Store partial result and update UI immediately
            task_data = self.pending_tasks[task_id]
            if 'partial_results' not in task_data:
                task_data['partial_results'] = []

            task_data['partial_results'].append(partial_result)

            # Create a real-time update panel
            partial_panel = self._create_partial_results_panel(task_data['partial_results'], progress)
            task_data['partial_panel'] = partial_panel

            print(f"📊 Partial result {len(task_data['partial_results'])} available for task {task_id}")

    def _on_fact_check_complete(self, task_id: str, fact_check_results: list = None, error: str = None):
        """Callback when async fact-checking completes"""
        print(f"Async fact-checking completed for task {task_id}")

        if error:
            print(f"Fact-checking error: {error}")
            return

        if fact_check_results and task_id in self.pending_tasks:
            task_data = self.pending_tasks[task_id]
            try:
                # Format the response with fact-check results
                formatted_response, fact_check_panel = format_message_with_citations(
                    task_data['response'], fact_check_results
                )

                # Store the updated result for UI refresh
                task_data['updated_response'] = formatted_response
                task_data['fact_check_panel'] = fact_check_panel
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

        return {
            'status': task.status.value,
            'progress': task.progress,
            'error': task.error,
            'completed': task.status == TaskStatus.COMPLETED
        }

    def _create_partial_results_panel(self, partial_results: list, progress: float) -> str:
        """Create HTML for partial results panel showing real-time progress"""
        from ui.components import create_fact_check_panel

        if not partial_results:
            return ""

        # Show completed results
        panel_html = f"""
        <div class="fact-check-partial">
            <div class="progress-header">
                <div class="progress-text">
                    🔄 Fact-checking in progress: {len(partial_results)} of {len(partial_results) + int((1 - progress) * 10)} citations completed
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {progress * 100}%"></div>
                </div>
            </div>
            <div class="partial-results">
        """

        # Show completed results
        for i, result in enumerate(partial_results):
            citation_id = f"partial_{i + 1}"
            comment_html = self._create_partial_citation_comment(citation_id, result)
            panel_html += comment_html

        panel_html += """
            </div>
        </div>
        """

        return panel_html

    def _create_partial_citation_comment(self, citation_id: str, result) -> str:
        """Create HTML for a partial citation comment"""
        import html

        # Truncate citation text for display
        citation_display = result.citation.text
        if len(citation_display) > 60:
            citation_display = citation_display[:57] + "..."

        status_class = self._get_status_class(result.verification_status)
        status_display = self._get_status_display(result.verification_status)

        # Create sources HTML
        sources_html = ""
        if result.sources_found:
            sources_html = '<div class="comment-sources">'
            sources_html += '<div class="sources-title">Sources Found:</div>'

            for source in result.sources_found[:3]:  # Show max 3 sources
                title = html.escape(source.get("title", "Untitled")[:50])
                url = html.escape(source.get("url", ""))

                sources_html += f"""
                <div class="source-item">
                    <a href="{url}" target="_blank" class="source-title" rel="noopener noreferrer">
                        {title}
                    </a>
                    <div class="source-url">{url}</div>
                </div>
                """

            sources_html += "</div>"

        # Confidence score
        confidence_html = f"""
        <div class="confidence-score">
            Confidence: {result.confidence:.1%}
        </div>
        """

        comment_html = f"""
        <div class="citation-comment partial-result" data-citation-id="{citation_id}">
            <div class="comment-header">
                <div class="comment-citation-text">{html.escape(citation_display)}</div>
                <div class="comment-status">
                    <span class="status-badge {status_class}">{status_display}</span>
                    <span class="partial-badge">✓</span>
                </div>
            </div>
            <div class="comment-content" id="content_{citation_id}">
                <div class="comment-explanation">
                    {html.escape(result.explanation)}
                </div>
                {sources_html}
                {confidence_html}
            </div>
        </div>
        """

        return comment_html

    def _get_status_class(self, status: str) -> str:
        """Get CSS class for verification status"""
        status_classes = {
            "verified": "status-verified citation-verified",
            "not_found": "status-not-found citation-not-found",
            "contradicted": "status-contradicted citation-contradicted",
            "error": "status-error citation-error",
            "partial": "status-not-found citation-not-found",
        }
        return status_classes.get(status, "status-error citation-error")

    def _get_status_display(self, status: str) -> str:
        """Get display text for verification status"""
        status_displays = {
            "verified": "Verified",
            "not_found": "Not Found",
            "contradicted": "Contradicted",
            "error": "Error",
            "partial": "Partial",
        }
        return status_displays.get(status, "Unknown")

    def get_task_result(self, task_id: str) -> dict:
        """Get the result of a completed async task"""
        if task_id not in self.pending_tasks:
            return None

        task_data = self.pending_tasks.get(task_id, {})
        if task_data.get('completed'):
            return {
                'formatted_response': task_data.get('updated_response'),
                'fact_check_panel': task_data.get('fact_check_panel')
            }
        return None

    def _get_usage_html(self) -> str:
        """Generate HTML for usage statistics panel"""
        try:
            from usage_tracker import usage_tracker

            # Get daily statistics
            daily_stats = usage_tracker.get_daily_stats()

            html = f"""
            <div class="usage-stats">
                <h3>📊 Usage Statistics (Last 24 Hours)</h3>

                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="stat-number">{daily_stats.total_calls}</div>
                        <div class="stat-label">Total Calls</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${daily_stats.total_cost_usd:.4f}</div>
                        <div class="stat-label">Total Cost</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{daily_stats.successful_calls}</div>
                        <div class="stat-label">Successful</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{daily_stats.total_tokens:,}</div>
                        <div class="stat-label">Tokens Used</div>
                    </div>
                </div>

                <div class="success-rate">
                    <strong>Success Rate:</strong> {daily_stats.successful_calls/max(1, daily_stats.total_calls)*100:.1f}%
                </div>

                <div class="avg-duration">
                    <strong>Avg Duration:</strong> {daily_stats.average_duration:.2f}s
                </div>
            """

            if daily_stats.provider_breakdown:
                html += """
                <div class="provider-breakdown">
                    <h4>🏢 Provider Breakdown</h4>
                """
                for provider, stats in daily_stats.provider_breakdown.items():
                    success_rate = stats['successful_calls'] / max(1, stats['calls']) * 100
                    html += f"""
                    <div class="provider-stat">
                        <span class="provider-name">{provider.upper()}</span>
                        <span class="provider-calls">{stats['calls']} calls</span>
                        <span class="provider-cost">${stats['cost_usd']:.4f}</span>
                        <span class="provider-success">{success_rate:.1f}%</span>
                    </div>
                    """
                html += "</div>"

            if daily_stats.top_endpoints:
                html += """
                <div class="top-endpoints">
                    <h4>🔝 Top Endpoints</h4>
                """
                for i, endpoint in enumerate(daily_stats.top_endpoints[:5], 1):
                    html += f"""
                    <div class="endpoint-stat">
                        <span class="endpoint-rank">{i}.</span>
                        <span class="endpoint-name">{endpoint['endpoint']}</span>
                        <span class="endpoint-calls">{endpoint['calls']} calls</span>
                    </div>
                    """
                html += "</div>"

            html += """
            </div>

            <style>
            .usage-stats {
                padding: 15px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            .stat-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 20px 0;
            }
            .stat-card {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                text-align: center;
                border: 1px solid #e9ecef;
            }
            .stat-number {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 5px;
            }
            .stat-label {
                font-size: 12px;
                color: #6c757d;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .success-rate, .avg-duration {
                margin: 10px 0;
                font-size: 14px;
            }
            .provider-breakdown, .top-endpoints {
                margin-top: 20px;
            }
            .provider-stat, .endpoint-stat {
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #f0f0f0;
                font-size: 13px;
            }
            .provider-name {
                font-weight: 600;
            }
            .provider-cost {
                color: #28a745;
                font-weight: 500;
            }
            .provider-success {
                color: #17a2b8;
            }
            .endpoint-rank {
                color: #6c757d;
                font-weight: 600;
            }
            .endpoint-calls {
                color: #6c757d;
            }
            </style>
            """

            return html

        except Exception as e:
            return f"<div class='error'>Error loading usage statistics: {str(e)}</div>"

    def _get_status_html(self) -> str:
        """Generate HTML for system status panel"""
        try:
            # Fill in dynamic values first
            chat_status = "✅ Ready" if self.chat_model and self.chat_model.validate_setup() else "❌ Error"
            search_status = "✅ Ready" if self.search_client and self.search_client.validate_setup() else "❌ Error"
            ner_status = "✅ Ready" if self.ner_extractor and self.ner_extractor.validate_setup() else "❌ Error"
            fact_check_status = "✅ Ready" if self.fact_checker and self.fact_checker.validate_setup() else "❌ Error"

            # Determine search backend
            search_backend = "Firecrawl"
            if hasattr(self.search_client, '__class__'):
                if "SearXNG" in str(type(self.search_client)):
                    search_backend = "SearXNG (Local)"
                elif "Mock" in str(type(self.search_client)):
                    search_backend = "Mock (Testing)"

            html = f"""
            <div class="system-status">
                <h3>🔧 System Status</h3>

                <div class="status-grid">
                    <div class="status-item">
                        <span class="status-label">Chat Model:</span>
                        <span class="status-value">{chat_status}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Search Client:</span>
                        <span class="status-value">{search_status}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">NER Extractor:</span>
                        <span class="status-value">{ner_status}</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Fact Checker:</span>
                        <span class="status-value">{fact_check_status}</span>
                    </div>
                </div>

                <div class="async-status">
                    <h4>🔄 Async Tasks</h4>
                    <div class="task-count">
                        Active Tasks: <span id="active-task-count">{len(self.pending_tasks)}</span>
                    </div>
                </div>

                <div class="system-info">
                    <h4>ℹ️ System Information</h4>
                    <div class="info-item">
                        <span class="info-label">Search Backend:</span>
                        <span class="info-value">{search_backend}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Usage Tracking:</span>
                        <span class="info-value">✅ Active</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Data File:</span>
                        <span class="info-value">usage_data.json</span>
                    </div>
                </div>
            </div>

            <style>
            .system-status {{
                padding: 15px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            .status-grid {{
                display: grid;
                gap: 10px;
                margin: 15px 0;
            }}
            .status-item {{
                display: flex;
                justify-content: space-between;
                padding: 8px 12px;
                background: #f8f9fa;
                border-radius: 6px;
                border: 1px solid #e9ecef;
                font-size: 13px;
            }}
            .status-label {{
                font-weight: 600;
                color: #495057;
            }}
            .status-value {{
                color: #28a745;
                font-weight: 500;
            }}
            .status-value.error {{
                color: #dc3545;
            }}
            .async-status, .system-info {{
                margin-top: 20px;
            }}
            .task-count {{
                font-size: 14px;
                padding: 8px 12px;
                background: #e3f2fd;
                border-radius: 6px;
                margin: 10px 0;
            }}
            .info-item {{
                display: flex;
                justify-content: space-between;
                padding: 6px 0;
                font-size: 13px;
            }}
            .info-label {{
                font-weight: 600;
                color: #495057;
            }}
            .info-value {{
                color: #17a2b8;
            }}
            </style>
            """

            return html

        except Exception as e:
            return f"<div class='error'>Error loading system status: {str(e)}</div>"


def chat_response(message, history):
    """Main chat response function"""
    if not message.strip():
        return history, ""

    # Convert history format and generate response
    try:
        # Convert Gradio messages format to our format
        converted_history = []
        if history:
            user_content = None
            for msg in history:
                if msg.get("role") == "user":
                    user_content = msg.get("content", "")
                elif msg.get("role") == "assistant" and user_content:
                    assistant_content = msg.get("content", "")
                    converted_history.append([user_content, assistant_content])
                    user_content = None

        response, fact_check_html, task_id = app.process_message(message, converted_history)

        # Add loading indicator if async fact-checking is running
        if task_id:
            print(f"📱 Creating loading HTML for task: {task_id}")
            fact_check_html = f"""
            <div class="fact-check-loading" id="task-{task_id}">
                <div style="display: flex; align-items: center; gap: 10px; padding: 20px;">
                    <div class="loading-spinner"></div>
                    <div>
                        <strong>Fact-checking citations...</strong>
                        <div style="font-size: 0.9em; color: #666; margin-top: 5px;">
                            This may take 30-45 seconds. Results will appear here automatically.
                        </div>
                        <div class="debug-info" style="font-size: 0.8em; color: #999; margin-top: 10px;">
                            Task ID: {task_id}
                        </div>
                    </div>
                </div>
            </div>
            """

        # Add new messages to history
        history = history or []
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})

        return history, fact_check_html
    except Exception as e:
        error_response = f"Error processing message: {str(e)}"
        history = history or []
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_response})
        return history, f"<p style='color: red;'>{error_response}</p>"


  
  

# Global app instance (created after class definition)
app = CitationFactChecker()


def create_interface():
    """Create the main Gradio interface"""

    # Load custom CSS
    css_path = os.path.join(os.path.dirname(__file__), "ui", "styles.css")
    custom_css = ""
    try:
        with open(css_path) as f:
            custom_css = f.read()
    except Exception as e:
        print(f"Could not load CSS: {e}")

    # Load custom JavaScript
    js_path = os.path.join(os.path.dirname(__file__), "ui", "citation_handlers.js")
    custom_js = ""
    try:
        with open(js_path) as f:
            js_content = f.read()
        print(f"✅ Loaded JavaScript from {js_path}")
        # Wrap the JavaScript in a function for Gradio's js parameter
        custom_js = f"""
        () => {{
            {js_content}

            // Async fact-checking functionality
            window.activeTasks = {{}};
            window.pollIntervals = {{}};

            // Auto-detect and start polling for new tasks
            function setupTaskObserver() {{
                // Create a MutationObserver to watch for new loading indicators
                const observer = new MutationObserver(function(mutations) {{
                    mutations.forEach(function(mutation) {{
                        mutation.addedNodes.forEach(function(node) {{
                            if (node.nodeType === Node.ELEMENT_NODE) {{
                                // Check if this is a loading indicator
                                const loadingElement = node.querySelector && node.querySelector('.fact-check-loading');
                                if (loadingElement) {{
                                    const taskId = loadingElement.id.replace('task-', '');
                                    if (taskId) {{
                                        console.log('🎯 Auto-detected new task:', taskId);
                                        startAsyncPolling(taskId, '#' + loadingElement.id);
                                    }}
                                }}
                                // Also check if the node itself is a loading indicator
                                if (node.classList && node.classList.contains('fact-check-loading')) {{
                                    const taskId = node.id.replace('task-', '');
                                    if (taskId) {{
                                        console.log('🎯 Auto-detected new task (direct):', taskId);
                                        startAsyncPolling(taskId, '#' + node.id);
                                    }}
                                }}
                            }}
                        }});
                    }});
                }});

                // Start observing the entire document
                observer.observe(document.body, {{
                    childList: true,
                    subtree: true
                }});

                console.log('👀 Task observer setup complete');
            }}

            window.startAsyncPolling = function(taskId, factCheckPanelSelector) {{
                console.log('🔄 Starting async polling for task:', taskId);
                console.log('🎯 Panel selector:', factCheckPanelSelector);

                if (window.pollIntervals[taskId]) {{
                    clearInterval(window.pollIntervals[taskId]);
                }}

                window.activeTasks[taskId] = {{
                    startTime: Date.now(),
                    pollCount: 0
                }};

                console.log('✅ Task registered, starting polling interval');
                window.pollIntervals[taskId] = setInterval(function() {{
                    window.pollAsyncTask(taskId, factCheckPanelSelector);
                }}, 2000); // Poll every 2 seconds

                // Timeout after 60 seconds
                setTimeout(function() {{
                    if (window.pollIntervals[taskId]) {{
                        clearInterval(window.pollIntervals[taskId]);
                        delete window.pollIntervals[taskId];
                        console.log('⏰ Polling timeout for task:', taskId);
                    }}
                }}, 60000);
            }};

            window.pollAsyncTask = function(taskId, factCheckPanelSelector) {{
                const task = window.activeTasks[taskId];
                if (!task) return;

                task.pollCount++;

                // Make AJAX request to check task status
                fetch('http://127.0.0.1:5001/task_status/' + taskId)
                    .then(response => response.json())
                    .then(data => {{
                        console.log('📊 Poll response for task', taskId, ':', data);

                        const panel = document.querySelector(factCheckPanelSelector);
                        if (!panel) {{
                            console.error('❌ Panel not found with selector:', factCheckPanelSelector);
                            return;
                        }}

                        // Handle partial results (real-time updates)
                        if (data.has_partial && data.partial_panel) {{
                            panel.innerHTML = data.partial_panel;
                            console.log('🔄 Updated panel with partial results for task:', taskId);
                        }}

                        // Handle completed task
                        if (data.completed && data.result) {{
                            // Task completed, update the UI
                            clearInterval(window.pollIntervals[taskId]);
                            delete window.pollIntervals[taskId];

                            panel.innerHTML = data.result.fact_check_panel;
                            console.log('✅ Async fact-checking completed for task:', taskId);
                            console.log('🎯 Final panel content length:', data.result.fact_check_panel.length);
                        }} else if (!data.has_partial) {{
                            console.log('⏳ Task not completed yet:', data);
                        }}
                    }})
                    .catch(error => {{
                        console.error('❌ Error polling task status:', error);
                    }});
            }};

            // Initialize the task observer to auto-detect new tasks
            setupTaskObserver();
            console.log('🚀 Async fact-checking system initialized');
        }}
        """
    except Exception as e:
        print(f"Could not load JavaScript: {e}")
        # Fallback to inline JS if file loading fails
        custom_js = """
        () => {
            console.log('🚀 Citation Needed: JavaScript loaded inline');
            window.citationDebug = function() {
                console.log('🔍 Debug info:', { location: window.location.href });
            };
            window.citationDebug();
        }
        """

    # Add additional CSS for better panel layout
    additional_css = """
    /* Ensure fact-check panel has adequate width and height */
    .gradio-container .gradio-row .gradio-column:last-child {
        min-width: 400px !important;
    }

    /* Make sure HTML components fill their containers */
    .gradio-html {
        height: 100%;
    }

    /* Improve scrolling for long content */
    .fact-check-panel {
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    /* Citation interaction styles */
    .active-highlight {
        box-shadow: 0 0 0 2px #2196F3;
        z-index: 10;
        position: relative;
    }

    .comment-content {
        display: none;
        padding: 12px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
    }

    .expand-icon {
        transition: transform 0.2s ease;
        font-size: 14px;
        user-select: none;
    }

    .expand-icon.expanded {
        transform: rotate(180deg);
    }

    .comment-header {
        cursor: pointer;
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 12px;
        border: 1px solid rgba(128, 128, 128, 0.1);
        border-radius: 6px;
        margin-bottom: 8px;
    }

    .comment-header:hover {
        background: rgba(128, 128, 128, 0.05);
    }

    .comment-citation-text {
        font-weight: 500;
        color: #333;
        line-height: 1.4;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    .comment-status {
        display: flex;
        align-items: center;
        gap: 8px;
        justify-content: flex-start;
    }
    """

    custom_css += additional_css

    # Create head content for additional script loading if needed
    head_content = """
    <script>
    console.log('🚀 Citation Needed: Head script executing');
    </script>
    """

    with gr.Blocks(
        title="Citation Needed",
        css=custom_css,
        head=head_content,
        js=custom_js
    ) as interface:
        # Debug info component to verify JS is loading
        gr.HTML("""
        <div style="display: none;" id="js-debug-info">
            <script>
            console.log('🚀 Citation Needed: Interface HTML component loaded');

            // Verify that our functions are available
            setTimeout(function() {
                console.log('🔍 Citation system check:', {
                    toggleComment: typeof window.toggleComment,
                    highlightCitation: typeof window.highlightCitation,
                    citationDebug: typeof window.citationDebug,
                    citationElements: document.querySelectorAll('.citation-comment').length,
                    highlightElements: document.querySelectorAll('.citation-highlight').length
                });

                // Auto-run debug if available
                if (typeof window.citationDebug === 'function') {
                    window.citationDebug();
                }
            }, 1000);
            </script>
        </div>
        """, visible=False)

        gr.Markdown("# Citation Needed")
        gr.Markdown("Chat with AI and get automatic fact-checking of academic citations")

        with gr.Row():
            # Main chat area (left side)
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="Chat",
                    height=600,
                    show_label=True,
                    elem_classes=["chat-container"],
                    type="messages"
                )

                msg = gr.Textbox(
                    label="Message", placeholder="Ask about academic topics...", lines=3
                )

                with gr.Row():
                    submit_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear")

            # Right side panel with tabs
            with gr.Column(scale=1):
                with gr.Tabs():
                    # Fact-check results tab
                    with gr.TabItem("Fact-Check Results"):
                        fact_check_panel = gr.HTML(
                            value="<div class='fact-check-empty'><p>Fact-checking results will appear here after you send a message.</p></div>",
                            elem_classes=["fact-check-panel"],
                        )

                    # Usage statistics tab
                    with gr.TabItem("Usage Statistics"):
                        usage_panel = gr.HTML(
                            value=app._get_usage_html(),
                            elem_classes=["usage-panel"],
                        )

                    # System status tab
                    with gr.TabItem("System Status"):
                        status_panel = gr.HTML(
                            value=app._get_status_html(),
                            elem_classes=["status-panel"],
                        )

        # Event handlers
        submit_btn.click(
            fn=chat_response,
            inputs=[msg, chatbot],
            outputs=[chatbot, fact_check_panel],
        ).then(
            lambda: "",  # Clear input
            outputs=[msg],
        )

        msg.submit(
            fn=chat_response,
            inputs=[msg, chatbot],
            outputs=[chatbot, fact_check_panel],
        ).then(
            lambda: "",  # Clear input
            outputs=[msg],
        )

        clear_btn.click(
            lambda: (
                [],
                "",
                "<div class='fact-check-empty'><p>Fact-checking results will appear here after you send a message.</p></div>",
                app._get_usage_html(),
                app._get_status_html(),
            ),
            outputs=[chatbot, msg, fact_check_panel, usage_panel, status_panel],
        )

    return interface


if __name__ == "__main__":
    # Check for required environment variables
    required_vars = ["OPENROUTER_API_KEY", "FIRECRAWL_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("Please copy .env.example to .env and fill in your API keys")

    # Create and launch interface
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        debug=True  # Enable debug mode for better development
    )
