"""AI-powered natural language question answering about fantasy football data."""

from fastapi import APIRouter
from models import AIRequest, AIResponse
from services.ai import ask_question

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post("/ask", response_model=AIResponse)
async def ask_ai(request: AIRequest):
    """Ask a natural language question about fantasy football data.

    The AI retrieves relevant data from the database and provides
    an answer grounded in actual statistics.
    """
    return await ask_question(request.question)
