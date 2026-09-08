from fastapi import APIRouter, Request, HTTPException
from ..mcp.connection import get_mcp_session

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/silpo/callback")
async def silpo_oauth_callback(request: Request, code: str):
    #заглушка для тестування
    mcp_token = "fake_token_for_now" 
    
    try:
        session = await get_mcp_session(mcp_token)
        return {"status": "success", "message": "Authorized in Silpo MCP"}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Silpo token")