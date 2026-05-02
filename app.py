from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


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
        if "challenge" in payload:
            return JSONResponse({"challenge": payload["challenge"]})
        if "CHALLENGE" in payload:
            return JSONResponse({"challenge": payload["CHALLENGE"]})
        if payload.get("type") == "url_verification":
            return JSONResponse({"challenge": payload.get("challenge", "")})

        from feishu_bot import FeishuApiError, FeishuConfigError, handle_feishu_event

        return JSONResponse(handle_feishu_event(payload))
    except ImportError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    except Exception as exc:
        try:
            from feishu_bot import FeishuApiError, FeishuConfigError
        except ImportError:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

        if isinstance(exc, FeishuConfigError):
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
        if isinstance(exc, FeishuApiError):
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
