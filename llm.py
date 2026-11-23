"""
llm.py - talking to the AI model

One small function, ask_model(). It works with three kinds of provider, chosen in the .env file:

  LLM_PROVIDER=openrouter   (default) a FREE NVIDIA model through OpenRouter
  LLM_PROVIDER=openai       OpenAI (paid)
  LLM_PROVIDER=custom       any other provider that copies OpenAI's API, for example the free tiers of
                            Groq or Google Gemini. You give it a web address, a key and a model name.

All three use the same "openai" Python package. The only differences are the web address, the key and the model name.
"""

import os

from dotenv import load_dotenv
from openai import APIError, OpenAI

load_dotenv()  # read the .env file

PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()

if PROVIDER == "openai":
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=120, max_retries=4)

elif PROVIDER == "custom":
    MODEL = os.getenv("LLM_MODEL", "")
    client = OpenAI(
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
        timeout=120,
        max_retries=4,
    )

else:
    MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-super-vl:free")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        timeout=120,
        max_retries=4,       # free models are rate limited, so we retry politely
    )


class ModelUnavailable(Exception):
    """The AI model could not be reached or refused the request (for example a free daily limit)."""


def ask_model(system_text, user_text):
    """Send one question to the model and return its reply as text."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            temperature=0,       # 0 = the most predictable answers
            max_tokens=3000,     # some free models "think" first, and thinking uses tokens too
        )
    except APIError as error:
        text = str(error).lower()
        message = "The AI model is not available right now."
        if "free-models-per-day" in text:
            message = ("The free daily limit of the OpenRouter free models is used up. Try again tomorrow, add credits on OpenRouter, "
                       "or switch provider in .env (LLM_PROVIDER=custom with Groq or Gemini, or LLM_PROVIDER=openai).")
        elif "429" in text or "rate limit" in text:
            message = "The AI model's rate limit was reached. Wait a minute and try again."
        raise ModelUnavailable(message)

    text = response.choices[0].message.content
    if text is None:
        return ""
    return text


def check_setup():
    """Return a helpful message if something is missing in .env, or "" if everything looks fine."""
    if PROVIDER == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            return "Add OPENAI_API_KEY to your .env file."
    elif PROVIDER == "custom":
        for name in ["LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"]:
            if not os.getenv(name):
                return "LLM_PROVIDER=custom needs " + name + " in your .env file (see .env.example)."
    else:
        if not os.getenv("OPENROUTER_API_KEY"):
            return "Add OPENROUTER_API_KEY to your .env file (free key: https://openrouter.ai/keys)."
    return ""
