"""开发环境启动入口。"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app="src.api.app:app",
        host="0.0.0.0",
        port=7000,
        reload=True,
    )
