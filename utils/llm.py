import os
import json
import re
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

T = TypeVar("T", bound=BaseModel)

def get_active_provider() -> str:
    """Return active provider: 'gemini' if GEMINI_API_KEY or GOOGLE_API_KEY set, else 'openai'."""
    explicit_provider = os.getenv("LLM_PROVIDER", "").lower()
    if explicit_provider in ["gemini", "google"]:
        return "gemini"
    if explicit_provider == "openai":
        return "openai"

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        return "gemini"

    return "openai"

def _raw_gemini_call(api_key: str, system_prompt: str, user_prompt: str, model_name: str) -> str:
    """Call Google Gemini API with JSON output mode using official google.genai SDK."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        temperature=0.2
    )
    response = client.models.generate_content(
        model=model_name,
        contents=user_prompt,
        config=config
    )
    return response.text or ""



# --- OpenAI API Call ---
def get_openai_client():
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise ValueError("OPENAI_API_KEY is not configured in .env or environment variables.")
    return OpenAI(api_key=api_key)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def _raw_openai_call(client, system_prompt: str, user_prompt: str, model_name: str) -> str:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    return response.choices[0].message.content or ""

# --- Primary Entry Point ---
def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    output_schema: Type[T],
    model_name: Optional[str] = None
) -> T:
    """
    Call LLM (Gemini or OpenAI), forcing JSON output and validating against Pydantic schema.
    Supports automatic cross-provider fallback.
    """
    primary_provider = get_active_provider()
    providers_to_try = [primary_provider, "openai" if primary_provider == "gemini" else "gemini"]
    
    schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
    augmented_user_prompt = (
        f"{user_prompt}\n\n"
        f"CRITICAL: Your output MUST strictly be valid JSON matching this schema:\n"
        f"```json\n{schema_json}\n```\n"
        f"Output ONLY the JSON object."
    )

    last_error = None
    for provider in providers_to_try:
        for attempt in range(2):
            try:
                if provider == "gemini":
                    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                    if not api_key or api_key in ["your_gemini_api_key_here", "your_google_api_key_here"]:
                        raise ValueError("GEMINI_API_KEY / GOOGLE_API_KEY is not configured in .env.")
                    target_model = model_name or os.getenv("GEMINI_MODEL", "gemini-flash-latest")
                    print(f"🤖 [LLM] Calling Gemini API (Model: {target_model})...")
                    raw_text = _raw_gemini_call(api_key, system_prompt, augmented_user_prompt, target_model)
                else:
                    client = get_openai_client()
                    target_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                    print(f"🤖 [LLM] Calling OpenAI API (Model: {target_model})...")
                    raw_text = _raw_openai_call(client, system_prompt, augmented_user_prompt, target_model)

                # Clean markdown wrapping if present
                cleaned_text = raw_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()

                parsed_data = json.loads(cleaned_text)
                validated = output_schema.model_validate(parsed_data)
                return validated
            except (json.JSONDecodeError, ValidationError, ValueError, Exception) as e:
                last_error = e
                print(f"⚠️ Warning: LLM ({provider}) returned error (attempt {attempt + 1}/2): {e}")
                augmented_user_prompt += f"\n\nYour previous response failed validation with error: {e}. Please fix and return ONLY valid JSON."

    raise ValueError(f"Failed to obtain valid JSON matching {output_schema.__name__} from LLMs: {last_error}")

