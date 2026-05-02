from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from feishu_bot import FeishuApiError, FeishuConfigError, handle_feishu_event


app = FastAPI()


@app.get("/")
async def home():
    return {"ok": True, "service": "feishu-meme-bot"}


@app.get("/api/feishu")
async def feishu_health():
    return {"ok": True, "service": "feishu-meme-bot"}


@app.post("/api/feishu")
async def feishu_callback(request: Request):
    try:
        payload = await request.json()
        return JSONResponse(handle_feishu_event(payload))
    except FeishuConfigError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    except FeishuApiError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

