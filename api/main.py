from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Optional, List, Dict, Any

import plotly.io as pio

# your existing imports
from financial_core import process_request
from gmini import chat_financial_assistant

app = FastAPI(title="Persian Financial Chatbot API")

# ✅ IMPORTANT: later replace with your Lovable domain only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://mohammadreza-sheikholeslami.lovable.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    # send last few messages from frontend so backend can build history_text
    history: Optional[List[Dict[str, str]]] = None  # [{"role":"user/assistant","content":"..."}]


class ChatResponse(BaseModel):
    type: Literal["text", "image"]
    answer: Optional[str] = None
    plotly_json: Optional[str] = None
    caption: Optional[str] = None


@app.get("/health")
def health():
    return {"ok": True}


def build_history_text(history: Optional[List[Dict[str, str]]]) -> str:
    if not history:
        return ""

    # similar to your streamlit: last 5 messages
    recent = history[-5:]
    lines = []
    for msg in recent:
        role = msg.get("role", "")
        content = msg.get("content", "")
        role_prefix = "کاربر:" if role == "user" else "دستیار:"
        lines.append(f"{role_prefix} {content}")
    return "\n".join(lines) + "\n"


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    user_input = (req.message or "").strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Empty message")

    history_text = build_history_text(req.history)

    try:
        # Same as your streamlit:
        features = process_request(user_input)
        response_type = features.get("type")

        if response_type == "image":
            fig = features.get("image")
            caption = features.get("caption")

            if fig is None:
                raise HTTPException(status_code=500, detail="No figure returned")

            # Convert plotly figure to JSON string (exactly like your DB storage)
            plotly_json = fig.to_json() if hasattr(fig, "to_json") else str(fig)

            return ChatResponse(
                type="image",
                plotly_json=plotly_json,
                caption=caption
            )

        # Else: text response from your LLM function
        full_response = chat_financial_assistant(user_input, history_text)

        return ChatResponse(
            type="text",
            answer=full_response
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
