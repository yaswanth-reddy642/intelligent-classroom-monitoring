"""Run the backend server: python -m backend.run"""

import os
import uvicorn
from backend.app.core.config import get_settings


def main():
    settings = get_settings()
    port = int(os.environ.get("PORT", settings.backend_port))
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
