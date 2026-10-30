from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .config import settings
from .database import Base, engine
 #ensure_schema
from .api import router
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)
#ensure_schema()
app=FastAPI(title=settings.app_name, version="0.1.0")
origins = [origin.strip().rstrip("/") for origin in settings.cors_origins.split(",") if origin.strip()]
app.include_router(router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates=Jinja2Templates(directory="app/templates")

@app.get("/health")
def health(): return {"status":"ok"}
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# @app.get("/", response_class=HTMLResponse)
# def home(request:Request): return templates.TemplateResponse("index.html", {"request":request,"app_name":settings.app_name})


@app.get("/", response_class=HTMLResponse)
def home(request: Request): 
    # Pass request as its own keyword argument, and context as a separate dictionary
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"app_name": settings.app_name}
    )

