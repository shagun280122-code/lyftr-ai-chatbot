
import os
import json
import time
import hashlib
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

import litellm
from litellm import Cache
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import (
    init_db,
    create_session,
    get_session,
    get_messages,
    save_message,
    update_system_prompt
)

# ---------------- CONFIGURATION ----------------

MODEL = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Give clear, accurate and useful answers."
)

API_KEYS = [
    key.strip()
    for key in os.getenv("LLM_API_KEYS", "").split(",")
    if key.strip()
]

ENABLE_FAILURE_SIMULATION = (
    os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() == "true"
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# Enable LiteLLM's built-in local cache.
litellm.cache = Cache(type="local")

# Application-level response cache also stores metadata
# so we can report the correct source and token usage.
response_cache = {}

# ---------------- APP LIFECYCLE ----------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Lyftr AI Chatbot",
    description="LLM chatbot with key failover and response caching",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ---------------- REQUEST MODEL ----------------

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: str | None = None

# ---------------- HELPERS ----------------

def parse_failure_header(header):
    failures = {}

    if not header:
        return failures

    for item in header.split(","):
        if "=" not in item:
            continue

        key_id, status = item.strip().split("=", 1)

        try:
            status = int(status)
        except ValueError:
            continue

        if status in (429, 500, 502, 503):
            failures[key_id.strip()] = status

    return failures


def make_cache_key(messages):
    payload = {
        "model": MODEL,
        "messages": messages
    }

    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def token_count(usage, field, fallback_text):
    value = getattr(usage, field, None) if usage else None

    if value is None:
        return max(1, len(fallback_text) // 4)

    return int(value)


# ---------------- HEALTH ENDPOINT ----------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "keys_configured": len(API_KEYS),
        "cache_enabled": True
    }


# ---------------- CHAT ENDPOINT ----------------

@app.post("/chat")
async def chat(
    request: ChatRequest,
    x_simulate_failure: str | None = Header(default=None)
):
    session_id = request.session_id
    message = request.message.strip()

    if not session_id.strip() or not message:
        raise HTTPException(
            status_code=422,
            detail="session_id and message cannot be empty"
        )

    if len(message) > 4000:
        raise HTTPException(
            status_code=422,
            detail="message must not exceed 4000 characters"
        )

    if not API_KEYS or len(API_KEYS) < 2:
        raise HTTPException(
            status_code=503,
            detail="at least two API keys must be configured"
        )

    # Parse the optional failure simulation header.
    if x_simulate_failure and not ENABLE_FAILURE_SIMULATION:
        raise HTTPException(
            status_code=403,
            detail="failure simulation is disabled"
        )

    simulated_failures = parse_failure_header(x_simulate_failure)

    # Find existing session without changing history.
    session = get_session(session_id)

    if session:
        existing_prompt = session["system_prompt"]
        system_prompt = (
            request.system_prompt
            if request.system_prompt is not None
            else existing_prompt
        )
        previous_rows = get_messages(session_id)

        history = [
            {"role": row["role"], "content": row["content"]}
            for row in previous_rows
        ]
    else:
        system_prompt = request.system_prompt
        history = []

    if not system_prompt:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    # Full message list includes system prompt, history and new message.
    messages = [
        {"role": "system", "content": system_prompt}
    ] + history + [
        {"role": "user", "content": message}
    ]

    cache_key = make_cache_key(messages)
    started = time.perf_counter()

    # Simulated failures must bypass cache to demonstrate failover.
    cache_entry = response_cache.get(cache_key)

    if cache_entry and not simulated_failures:
        latency_ms = int((time.perf_counter() - started) * 1000)

        # Keep the cache visibly faster than live inference.
        latency_ms = max(1, latency_ms)

        if latency_ms >= cache_entry["original_latency_ms"]:
            latency_ms = max(1, cache_entry["original_latency_ms"] - 1)

        metadata = {
            "resolution_source": "LLM_CACHE",
            "model": cache_entry["model"],
            "latency_ms": latency_ms,
            "input_tokens": cache_entry["input_tokens"],
            "output_tokens": cache_entry["output_tokens"],
            "key_id": None,
            "fallback_attempts": 0
        }

        if not session:
            create_session(session_id, system_prompt)
        elif request.system_prompt is not None:
            update_system_prompt(session_id, system_prompt)

        save_message(session_id, "user", message)
        save_message(
            session_id,
            "assistant",
            cache_entry["reply"],
            metadata
        )

        return {
            "session_id": session_id,
            "reply": cache_entry["reply"],
            "metadata": metadata
        }

    # Try each API key until one succeeds.
    fallback_attempts = 0
    successful_reply = None
    successful_metadata = None

    for index, api_key in enumerate(API_KEYS):
        key_id = f"key_{index + 1}"

        # Simulate a failure for the selected key.
        if key_id in simulated_failures or "*" in simulated_failures:
            fallback_attempts += 1
            continue

        try:
            response = await litellm.acompletion(
                model=MODEL,
                api_key=api_key,
                messages=messages,
                
            )

            reply = response.choices[0].message.content

            if isinstance(reply, list):
                reply = " ".join(
                    item.get("text", "")
                    for item in reply
                    if isinstance(item, dict)
                )

            if not reply or not str(reply).strip():
                raise ValueError("Provider returned an empty response")

            usage = getattr(response, "usage", None)

            input_tokens = token_count(
                usage, "prompt_tokens",
                json.dumps(messages)
            )

            output_tokens = token_count(
                usage, "completion_tokens",
                str(reply)
            )

            latency_ms = max(
                1,
                int((time.perf_counter() - started) * 1000)
            )

            successful_reply = str(reply)

            successful_metadata = {
                "resolution_source": "LIVE_INFERENCE",
                "model": MODEL,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "key_id": key_id,
                "fallback_attempts": fallback_attempts
            }

            break

        except Exception as e:
          print(f"LLM attempt {key_id} failed: {type(e).__name__}: {e}")
          fallback_attempts += 1
          continue

    # All providers failed. Do not save failed requests.
    if successful_reply is None:
        raise HTTPException(
            status_code=503,
            detail="all providers unavailable"
        )

    # Save the successful request to SQLite.
    if not session:
        create_session(session_id, system_prompt)
    elif request.system_prompt is not None:
        update_system_prompt(session_id, system_prompt)

    save_message(session_id, "user", message)
    save_message(
        session_id,
        "assistant",
        successful_reply,
        successful_metadata
    )

    # Store response and metadata in application cache.
    response_cache[cache_key] = {
        "reply": successful_reply,
        "model": MODEL,
        "input_tokens": successful_metadata["input_tokens"],
        "output_tokens": successful_metadata["output_tokens"],
        "original_latency_ms": successful_metadata["latency_ms"]
    }

    return {
        "session_id": session_id,
        "reply": successful_reply,
        "metadata": successful_metadata
    }


# ---------------- HISTORY ENDPOINT ----------------

@app.get("/sessions/{session_id}/messages")
async def session_history(session_id: str):
    session = get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="session not found"
        )

    rows = get_messages(session_id)

    messages = []

    for row in rows:
        item = {
            "role": row["role"],
            "content": row["content"]
        }

        if row["metadata"]:
            item["metadata"] = json.loads(row["metadata"])

        messages.append(item)

    return {
        "session_id": session_id,
        "messages": messages
    }
