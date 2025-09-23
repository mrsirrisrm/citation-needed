import os

import dspy


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
        self.lm = dspy.OpenAI(
            api_key=self.openrouter_api_key,
            api_base="https://openrouter.ai/api/v1",
            model=self.chat_model_name,
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
        try:
            # Format conversation context
            context = ""
            if history:
                for user_msg, assistant_msg in history[-5:]:  # Last 5 exchanges
                    context += f"User: {user_msg}\nAssistant: {assistant_msg}\n"

            # Generate response
            result = self.chat_chain(context=context, user_message=message)

            return result.response

        except Exception as e:
            return f"Error generating response: {str(e)}"

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
