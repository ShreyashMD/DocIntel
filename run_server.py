from __future__ import annotations

import os

import uvicorn

from docintel._config import Config
from docintel.server.app import create_app


def main() -> None:
    config = Config(
        provider="gemini",
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        vector_store="memory",
        persist_dir=".docintel",
    )
    app = create_app(config)
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")


if __name__ == "__main__":
    main()
