import re
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.requests import Request


URL_REGEX = re.compile(
    r"https:\/\/(?:cdn|media).discord(?:app)?.(?:com|net)\/attachments\/.\d+\/\d+\/.*\.html"
)

client: httpx.AsyncClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    
    client = httpx.AsyncClient()
    yield
    await client.aclose()


app = FastAPI(lifespan=lifespan)


@app.head("/")
async def head():
    return {"message": "HEAD request received"}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/display")
async def display(url: str, req: Request):
    is_property = req.query_params.get("is")
    if not is_property:
        return {"error": "Invalid URL format"}

    hm_property = req.query_params.get("hm")
    if not hm_property:
        return {"error": "Invalid URL format"}

    url += f"&is={is_property}&hm={hm_property}"

    if not URL_REGEX.match(url):
        return {"error": "Invalid URL format"}

    try:
        url_class = httpx.URL(url)
    except httpx.InvalidURL:
        return {"error": "Invalid URL"}
    resp = await client.get(url_class)

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return {"error": f"Request failed with status code {exc.response.status_code}"}

    content: bytes | None = None

    first_time = True
    async for data in resp.aiter_bytes(10000000):
        if first_time:
            content = data
            first_time = False
        else:
            return {"error": "File too large"}

    if content is None:
        return {"error": "No content received from the URL"}

    return HTMLResponse(content)
