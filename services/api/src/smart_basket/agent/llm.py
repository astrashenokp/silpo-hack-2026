import os

from google import genai

from .chat_models import ChatCommand
from .prompts import CHAT_SYSTEM_PROMPT


class GeminiChatInterpreter:
    def __init__(
        self,
        api_key=None,
        model=None,
    ):
        api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
        )

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = (
            model
            or os.getenv(
                "GEMINI_MODEL",
                "gemini-3.7-flash",
            )
        )

    def interpret(
        self,
        message: str,
    ) -> ChatCommand:

        message = message.strip()

        if not message:
            return ChatCommand(
                intent="unknown",
                original_message="",
            )

        full_input = f"""
        {CHAT_SYSTEM_PROMPT}

        User message:
        {message}
        """

        interaction = (
            self.client
            .interactions
            .create(
                model=self.model,
                input=full_input,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": (
                        ChatCommand
                        .model_json_schema()
                    ),
                },
            )
        )

        if not interaction.output_text:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        command = (
            ChatCommand
            .model_validate_json(
                interaction.output_text
            )
        )

        return command.model_copy(
            update={
                "original_message": message
            }
        )