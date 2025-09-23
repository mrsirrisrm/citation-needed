import os

import gradio as gr
from dotenv import load_dotenv

# Import our components
from models.chat_model import create_chat_model
from models.fact_checker import create_fact_checker
from models.ner_extractor import create_ner_extractor
from search.firecrawl_client import create_search_client
from ui.components import format_message_with_citations


# Load environment variables
load_dotenv()


class CitationFactChecker:
    """Main application class that coordinates all components"""

    def __init__(self):
        """Initialize all components"""
        self.search_client = None
        self.chat_model = None
        self.ner_extractor = None
        self.fact_checker = None

        self._initialize_components()

    def _initialize_components(self):
        """Initialize all components with error handling"""
        try:
            print("Initializing search client...")
            self.search_client = create_search_client()
            print(f"Search client: {'✓' if self.search_client.validate_setup() else '✗'}")
        except Exception as e:
            print(f"Search client error: {e}")

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

    def process_message(self, message: str, history: list[list[str]]) -> tuple[str, str]:
        """
        Process a chat message and return response with fact-checking

        Args:
            message: User message
            history: Chat history

        Returns:
            Tuple of (chat_response, fact_check_panel_html)
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

        # Step 3: Fact-check citations
        fact_check_results = []
        if citations and self.fact_checker:
            try:
                fact_check_results = self.fact_checker.fact_check_citations(citations)
                print(f"Fact-checked {len(fact_check_results)} citations")
            except Exception as e:
                print(f"Fact-checking error: {e}")

        # Step 4: Format response with citations
        try:
            formatted_response, fact_check_panel = format_message_with_citations(
                response, fact_check_results
            )
        except Exception as e:
            formatted_response = response
            fact_check_panel = f"<p>Error formatting results: {str(e)}</p>"

        return formatted_response, fact_check_panel


# Global app instance
app = CitationFactChecker()


def chat_response(message, history):
    """Main chat response function"""
    if not message.strip():
        return history

    # Add user message to history
    history = history or []
    history.append([message, ""])

    # Generate response and fact-check
    try:
        response, fact_check_html = app.process_message(message, history[:-1])

        # Update the last response in history
        history[-1][1] = response

        return history, fact_check_html
    except Exception as e:
        error_response = f"Error processing message: {str(e)}"
        history[-1][1] = error_response
        return history, f"<p style='color: red;'>{error_response}</p>"


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

    with gr.Blocks(
        title="Citation Fact-Checker", theme=gr.themes.Soft(), css=custom_css
    ) as interface:
        gr.Markdown("# Citation Fact-Checker")
        gr.Markdown("Chat with AI and get automatic fact-checking of academic citations")

        # System status
        with gr.Row():
            gr.Markdown(f"""
            **System Status:**
            - Chat Model: {"✓" if app.chat_model and app.chat_model.validate_setup() else "✗"}
            - Citation NER: {"✓" if app.ner_extractor and app.ner_extractor.validate_setup() else "✗"}
            - Fact Checker: {"✓" if app.fact_checker and app.fact_checker.validate_setup() else "✗"}
            - Search Client: {"✓" if app.search_client and app.search_client.validate_setup() else "✗"}
            """)

        with gr.Row():
            # Main chat area (left side)
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Chat", height=600, show_label=True, elem_classes=["chat-container"]
                )

                msg = gr.Textbox(
                    label="Message", placeholder="Ask about academic topics...", lines=3
                )

                with gr.Row():
                    submit_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear")

            # Fact-check panel (right side)
            with gr.Column(scale=1):
                gr.Markdown("### Fact-Check Results")
                fact_check_panel = gr.HTML(
                    value="<div class='fact-check-empty'><p>Fact-checking results will appear here after you send a message.</p></div>",
                    elem_classes=["fact-check-panel"],
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
            ),
            outputs=[chatbot, msg, fact_check_panel],
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
    interface.launch(server_name="0.0.0.0", server_port=7860, show_error=True)
