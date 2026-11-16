"""Agentic RAG pipeline for Day 7 with real LLM Controller (OpenAI GPT-4o-mini / Gemini Flash)
and Hybrid Retriever (Dense Embedding + TF-IDF RRF).

Follows starter/agentic.py contracts and protocols.
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
import openai
from dotenv import load_dotenv

day7_dir = Path(__file__).resolve().parents[1]
load_dotenv(day7_dir / ".env")
sys.path.insert(0, str(day7_dir / "starter"))
from baseline import pack_context
from agentic import Controller, Retriever, run_agent


OPENAI_SYSTEM_PROMPT = """Bạn là Controller cho hệ thống Agentic RAG Sổ tay sinh viên ĐHBK Hà Nội.
Nhiệm vụ: Dựa vào câu hỏi và ngữ cảnh được cung cấp, hãy quyết định hành động tiếp theo:
1. NẾU CHƯA CÓ NGỮ CẢNH HOẶC NGỮ CẢNH CHƯA ĐỦ THÔNG TIN:
   - Hãy chọn action "search" kèm query ngắn gọn đúng trọng tâm.
   - Định dạng JSON: {"action": "search", "query": "<từ khóa tìm kiếm>"}

2. NẾU NGỮ CẢNH ĐÃ CÓ BẰNG CHỨNG HỖ TRỢ ĐỂ TRẢ LỜI:
   - Bạn BẮT BUỘC trả lời câu hỏi dựa trên bằng chứng trong ngữ cảnh.
   - Chèn trích dẫn [chunk_id] vào câu trả lời, và thêm chunk_id đó vào mảng 'citations'.
   - MỌI chunk_id trong 'citations' BẮT BUỘC phải nằm trong ngữ cảnh và xuất hiện dạng [chunk_id] trong trường 'answer'.
   - Định dạng JSON: {"action": "answer", "answer": "<nội dung câu trả lời kèm [chunk_id]>", "citations": ["<chunk_id>"]}

3. NẾU NGỮ CẢNH HOÀN TOÀN KHÔNG CÓ THÔNG TIN (câu hỏi ngoài phạm vi tài liệu):
   - Tuyệt đối không bịa đặt hoặc suy diễn ngoài ngữ cảnh.
   - Định dạng JSON: {"action": "answer", "answer": "Không đủ bằng chứng để trả lời.", "citations": []}
"""


def _sanitize_action(action: dict[str, Any], available_chunk_ids: list[str]) -> dict[str, Any]:
    """Sanitize citations ensuring chunk_ids exist in context and [chunk_id] is in answer text."""
    if action.get("action") == "answer":
        ans = action.get("answer", "")
        citations = action.get("citations", [])
        if citations:
            valid_cits = [c for c in citations if c in available_chunk_ids]
            for c in valid_cits:
                if f"[{c}]" not in ans:
                    ans += f" [{c}]"
            action["answer"] = ans
            action["citations"] = valid_cits
    return action


class OpenAIAgentController:
    """Controller using OpenAI API (gpt-4o-mini)."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.0
    ) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY not found in environment or .env file.")
        self.client = openai.OpenAI(api_key=key)
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = temperature

    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        available_chunk_ids = []
        if not history:
            user_content = f"Câu hỏi: {question}\nNgữ cảnh: Chưa có lượt tìm kiếm nào."
        else:
            last = history[-1]
            queries = last.get("queries", [])
            context = last.get("context", "")
            available_chunk_ids = last.get("context_ids", [])
            user_content = f"Câu hỏi: {question}\nNgữ cảnh tìm được:\n{context}\n\nCác mã chunk_id có thể trích dẫn: {available_chunk_ids}"

        for attempt in range(4):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content}
                    ],
                    response_format={"type": "json_object"},
                    temperature=self.temperature
                )
                raw_text = resp.choices[0].message.content or "{}"
                action = json.loads(raw_text)
                return _sanitize_action(action, available_chunk_ids)
            except Exception as e:
                time.sleep(1.5 * (attempt + 1))

        return {
            "action": "answer",
            "answer": "Không đủ bằng chứng để trả lời.",
            "citations": []
        }


class GeminiAgentController:
    """Controller using Google Gemini API with structured JSON output."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.0
    ) -> None:
        from google import genai
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY not found in environment or .env file.")
        self.client = genai.Client(api_key=key)
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.temperature = temperature

    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        available_chunk_ids = []
        if not history:
            prompt = f"{OPENAI_SYSTEM_PROMPT}\n\nCâu hỏi: {question}\nNgữ cảnh: Chưa có lượt tìm kiếm nào."
        else:
            last = history[-1]
            queries = last.get("queries", [])
            context = last.get("context", "")
            available_chunk_ids = last.get("context_ids", [])
            prompt = f"{OPENAI_SYSTEM_PROMPT}\n\nCâu hỏi: {question}\nNgữ cảnh tìm được:\n{context}\n\nCác mã chunk_id có thể trích dẫn: {available_chunk_ids}"

        for attempt in range(4):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "temperature": self.temperature
                    }
                )
                action = json.loads(response.text.strip())
                return _sanitize_action(action, available_chunk_ids)
            except Exception as e:
                time.sleep(2 * (attempt + 1))

        return {
            "action": "answer",
            "answer": "Không đủ bằng chứng để trả lời.",
            "citations": []
        }


def get_default_controller(temperature: float = 0.0) -> Controller:
    """Return an OpenAI controller if OPENAI_API_KEY is configured, else Gemini controller."""
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIAgentController(temperature=temperature)
    elif os.getenv("GEMINI_API_KEY"):
        return GeminiAgentController(temperature=temperature)
    else:
        raise ValueError("Neither OPENAI_API_KEY nor GEMINI_API_KEY found in environment or .env file.")
