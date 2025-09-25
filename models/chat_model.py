import os
import time

import dspy

from usage_tracker import APIProvider, track_api_call


class ChatSignature(dspy.Signature):
    """Generate a helpful response to the user's question"""

    context = dspy.InputField(desc="Previous conversation context")
    user_message = dspy.InputField(desc="Current user message")
    response = dspy.OutputField(desc="Helpful and informative response")


class ChatModel:
    """Model A: Main chat model using GPT-4"""

    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.chat_model_name = os.getenv("CHAT_MODEL", "openai/gpt-4-turbo-preview")

        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        # Configure DSPy with OpenRouter
        self.lm = dspy.LM(
            model=self.chat_model_name,
            api_key=self.openrouter_api_key,
            api_base="https://openrouter.ai/api/v1",
            max_tokens=2048,
            temperature=0.7,
        )

        # Set as default LM for DSPy
        dspy.settings.configure(lm=self.lm)

        # Initialize the chat chain
        self.chat_chain = dspy.ChainOfThought(ChatSignature)

    def chat(self, message: str, history: list[list[str]] = None) -> str:
        """
        Generate a chat response

        Args:
            message: Current user message
            history: Chat history as list of [user_msg, assistant_msg] pairs

        Returns:
            Assistant's response
        """
        start_time = time.time()
        success = True
        error_message = None
        tokens_used = 0
        result = None

        try:
            # Format conversation context
            context = ""
            if history:
                for user_msg, assistant_msg in history[-5:]:  # Last 5 exchanges
                    context += f"User: {user_msg}\nAssistant: {assistant_msg}\n"

            # Generate response
            result = self.chat_chain(context=context, user_message=message)

            # Try to extract token usage
            try:
                if hasattr(result, "__dict__") and hasattr(
                    result.__dict__.get("_lm", {}), "n_tokens"
                ):
                    tokens_used = result.__dict__["_lm"]["n_tokens"]
                elif hasattr(self.lm, "last_usage"):
                    tokens_used = self.lm.last_usage.get("total_tokens", 0)
            except Exception:
                pass  # Token extraction failed, but call was successful

            return result.response

        except Exception as e:
            success = False
            error_message = str(e)
            return f"Error generating response: {error_message}"

        finally:
            duration = time.time() - start_time
            track_api_call(
                provider=APIProvider.OPENROUTER,
                endpoint="chat_completion",
                duration=duration,
                success=success,
                tokens_used=tokens_used,
                error_message=error_message,
                metadata={
                    "model": self.chat_model_name,
                    "message_length": len(message),
                    "history_length": len(history) if history else 0,
                },
            )

    def validate_setup(self) -> bool:
        """Validate that the model is properly configured"""
        try:
            test_response = self.chat("Hello, this is a test message.")
            return len(test_response) > 0
        except Exception:
            return False


# Factory function for easy import
def create_chat_model() -> ChatModel:
    """Create and return a configured ChatModel instance"""
    return ChatModel()
