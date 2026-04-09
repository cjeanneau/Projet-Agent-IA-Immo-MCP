from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from src.app.monitoring.prometheus_metrics import track_inference_time
from langchain_core.runnables import RunnableConfig
import json
import time
from config_agent import llm_mistral, MCP_URL
from pydantic import BaseModel
from src.agents.clientMCP import create_client
from src.agents.agentMCP import create_agent
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]

router = APIRouter()
templates = Jinja2Templates(directory="src/app/templates")

# Langchain Timeout
config = RunnableConfig(metadata={"timeout": 5*60})

#session = rt.InferenceSession(str(DEPLOYED_MODEL_PATH))
#input_names = session.get_inputs()

async def get_agent(request: Request):
    """Lazy MCP connection — connects on first use."""
    app = request.app
    if app.state.agent is not None:
        return app.state.agent

    async with app.state._mcp_lock:
        # Double-check after acquiring lock
        if app.state.agent is not None:
            return app.state.agent

        client = await create_client(MCP_URL)
        tools = await client.get_tools()
        app.state.mcp_client = client
        app.state.mcp_tools = {t.name: t for t in tools}
        app.state.agent = await create_agent(tools=tools, llm=llm_mistral)
        return app.state.agent



@router.get("/", tags=["Home"], response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/healthcheck", tags=["Health"], response_class=JSONResponse)
async def home(request: Request):
    return {'status' : 'OK'}

@router.post("/predict", tags=["Prediction"])
async def predict(
    request : Request,
    type_local: str = Form(...),
    address: str = Form(...),
    surface_habitable: float = Form(...),
    nombre_pieces: int = Form(...),
    
    surface_terrain: Optional[float] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    address_type: Optional[str] = Form(None),
    ):
    print(type_local, address, surface_habitable, nombre_pieces, surface_terrain, latitude, longitude, address_type)
    try:
        await get_agent(request)
    except Exception:
        raise JSONResponse({"error" : "Error 503 : MCP server unavailable"})
    try:
        tool = request.app.state.mcp_tools["estimation_tools"]
        inference_start=time.time()
        context = await tool.ainvoke({
                "address" : address,
                "type_local" : type_local,
                "surface_habitable" : surface_habitable,
                "surface_terrain" : surface_terrain,
                "nombre_pieces" : nombre_pieces
            }
        )

        context = json.loads(context[0].get('text'))
        inference_time=time.time()-inference_start
        track_inference_time(inference_time*1000)
    except Exception as e:
        context = {
            "request": request,
            "error": str(e)
        }
        return templates.TemplateResponse("error.html", context, status_code=500)

    context['request'] = request
    
    return templates.TemplateResponse("prediction.html", context)

@router.get("/chatbot", tags=["Chat"], response_class=HTMLResponse)
async def chatbot(request: Request):
    return templates.TemplateResponse("chatbot.html", {"request": request})

@router.post("/chat", tags=["Chat"], response_class=JSONResponse)
async def chatbot(request: Request, body: ChatRequest):
    try:
        agent = await get_agent(request)
    except Exception:
        raise JSONResponse({"error" : "Error 503 : MCP server unavailable"})
    response = await agent.ainvoke(
        {"messages": [(m.role, m.content) for m in body.messages]},
        config =config
    )
    return JSONResponse(content={"message": response.get('messages')[-1].content})


@router.post("/chat/stream", tags=["Chat"])
async def chatbot(request: Request, body: ChatRequest):
    try:
        agent = await get_agent(request)
    except Exception:
        raise JSONResponse({"error" : "Error 503 : MCP server unavailable"})
    async def generate():
        async for event in agent.astream_events(
            {"messages": [(m.role, m.content) for m in body.messages]},
            config=config,
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield f"data: {json.dumps({'content': chunk.content})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")