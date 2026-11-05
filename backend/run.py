"""Run the backend server: python -m backend.run"""

import uvicorn
from backend.app.core.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
