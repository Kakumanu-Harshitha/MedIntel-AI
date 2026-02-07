from fastapi import APIRouter, Depends, HTTPException, Body, Request
from .auth import get_current_user
from .models import User
from . import mongo_memory, llm_service
from .audit_logger import audit_logger
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/feedback", tags=["Feedback"])

class FeedbackRequest(BaseModel):
    rating: str # "positive" or "negative"
    comment: Optional[str] = None
    context: Optional[str] = None # Optional context (e.g. summary of the report)

@router.post("/")
async def submit_feedback(
    request: Request,
    feedback: FeedbackRequest,
    current_user: User = Depends(get_current_user)
):
    user_id_str = str(current_user.id)
    mongo_memory.log_feedback(
        user_id=user_id_str,
        rating=feedback.rating,
        comment=feedback.comment,
        context=feedback.context
    )
    
    await audit_logger.log_event(
        action="USER_FEEDBACK",
        status="SUCCESS",
        user_id=current_user.id,
        request=request,
        metadata={
            "rating": feedback.rating,
            "has_comment": bool(feedback.comment),
            "refinement_triggered": feedback.rating == "negative"
        }
    )
    
    # If feedback is negative, trigger the Feedback Refiner Stage
    refinement_insight = None
    if feedback.rating == "negative" and llm_service.client:
        try:
            refiner_response = await llm_service.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": llm_service.PROMPT_FEEDBACK_REFINER.format(
                        feedback_rating=feedback.rating,
                        feedback_comment=feedback.comment or "No comment provided."
                    )}
                ],
                model=llm_service.LLM_MODEL
            )
            refinement_insight = refiner_response.choices[0].message.content
            # Store refinement insight for developers/admin review
            mongo_memory.store_message(user_id_str, "system_refinement", refinement_insight)
        except Exception as e:
            print(f"⚠️ Feedback Refiner Error: {e}")

    return {
        "message": "Feedback received",
        "refinement_triggered": feedback.rating == "negative",
        "insight_generated": refinement_insight is not None
    }
