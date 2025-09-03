from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from app.router import stores
from database import Base,engine

app =FastAPI()

#cors設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(stores.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



