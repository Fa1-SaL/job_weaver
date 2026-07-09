from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_jd_parser import get_valid_llm_output
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import Optional, Any, List, Dict
from pydantic import BaseModel
from llm_jd_parser import get_valid_llm_output
from history_cache import (
    get_cached_item,
    add_item,
    get_history_list,
    get_history_detail,
    delete_history_item,
    clear_history,
    _ensure_classifications,
)

class JDRequest(BaseModel):
    raw_jd: str
    url: Optional[str] = None
    client: str = "mercor"
    output_selection: Optional[Any] = None


def clean_input(text: str) -> str:
    """
    Makes raw JD safe and consistent before sending to LLM
    """
    if not text:
        return ""

    # normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # remove weird control characters
    text = "".join(ch for ch in text if ch.isprintable() or ch == "\n")

    # collapse excessive spacing
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join([line for line in lines if line])

    return text.strip()


@app.post("/parse-jd")
def parse_jd(request: JDRequest):
    try:
        print(f"Received request for client={request.client}")

        raw = clean_input(request.raw_jd)

        if not raw:
            return {
                "success": False,
                "error": "Empty JD provided"
            }

        # Check history cache
        cached_result = get_cached_item(raw, request.client, request.url)
        if cached_result:
            cached_result = _ensure_classifications(cached_result, "")
            print("Cache hit with complete classifications! Returning cached result.")
            return {
                "success": True,
                **cached_result,
                "cached": True
            }

        print("Calling LLM...")
        parsed_result = get_valid_llm_output(raw, url=request.url, client=request.client)
        parsed_result = _ensure_classifications(parsed_result, "")
        print("LLM finished")

        # Save to history cache
        add_item(raw, request.client, request.url, parsed_result)

        return {
            "success": True,
            **parsed_result,
            "cached": False
        }

    except Exception as e:
        print("ERROR:", str(e))
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/history")
def get_history():
    return {
        "success": True,
        "history": get_history_list()
    }


@app.get("/history/{item_id}")
def get_history_item(item_id: str):
    data = get_history_detail(item_id)
    if not data:
        return {"success": False, "error": "Item not found"}
    return {"success": True, "data": data}


@app.delete("/history/{item_id}")
def remove_history_item(item_id: str):
    success = delete_history_item(item_id)
    return {"success": success}


@app.delete("/history")
def purge_history():
    clear_history()
    return {"success": True}


@app.get("/")
def health_check():
    return {"status": "running"}