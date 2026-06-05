from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, stores, categories, shelves, displays, stats

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="连锁门店商品类目与陈列管理系统",
    description="管理连锁门店的商品类目树、货架分区和陈列状态",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(stores.router)
app.include_router(categories.router)
app.include_router(shelves.router)
app.include_router(displays.router)
app.include_router(stats.router)


@app.get("/")
def root():
    return {"message": "连锁门店商品类目与陈列管理系统 API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8014, reload=True)
