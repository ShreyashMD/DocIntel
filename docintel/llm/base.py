from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List


class BaseLLMClient(ABC):
    """Common interface for all LLM/embedding providers."""

    # ------------------------------------------------------------------
    # Embeddings — must be implemented by each provider
    # ------------------------------------------------------------------

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> List[float]: ...

    # ------------------------------------------------------------------
    # Generation — must be implemented by each provider
    # ------------------------------------------------------------------

    @abstractmethod
    def generate(self, prompt: str) -> str: ...

    # ------------------------------------------------------------------
    # Higher-level tasks — default implementations call generate()
    # ------------------------------------------------------------------

    def summarize(self, text: str, max_words: int = 120) -> str:
        prompt = (
            f"Summarize the following document in at most {max_words} words. "
            "Focus on the domain, main topics, and any key entities (equipment names, "
            "standards, procedures). Be concise.\n\n"
            f"{text[:8000]}"
        )
        return self.generate(prompt)

    def answer(self, question: str, context: str) -> str:
        prompt = (
            "You are an expert industrial document analyst. "
            "Answer the question strictly using the provided context. "
            "Cite sources inline using their number, e.g. [Source 1] or [Source 2, page 5]. "
            "Include the page number in the citation when it is shown in the source header. "
            "If the answer cannot be found in the context, say so explicitly.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {question}\n\n"
            "ANSWER:"
        )
        return self.generate(prompt)
