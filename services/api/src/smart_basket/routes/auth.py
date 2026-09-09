from fastapi import APIRouter, Request, HTTPException
from smart_basket.mcp.connection import get_mcp_session

router = APIRouter(prefix="/api/auth/silpo", tags=["auth"])

@router.get("/callback")
async def silpo_oauth_callback(request: Request, code: str, branch_id: str = None):
    # Тут буде реальний обмін коду на токен. Поки залишаємо плейсхолдер для команди
    real_token = "mcp_live_token_from_oauth" 
    
    # Зберігаємо токен та branchId у серверну сесію
    request.session["mcp_token"] = real_token
    if branch_id:
        request.session["branch_id"] = branch_id

    # Правильний виклик асинхронного контекстного менеджера
    try:
        async with get_mcp_session(real_token) as session:
            tools = await session.list_tools()
            tools_list = [t.name for t in tools.tools]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "tools_available": tools_list}