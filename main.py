from fastapi import FastAPI
from user import router as user_router
from tasks import router as task_router
from database import engine, Base

app = FastAPI()
app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(task_router, prefix="/tasks", tags=["tasks"])

Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {"message": "Hello World"}