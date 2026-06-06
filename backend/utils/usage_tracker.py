from database.database import save_api_usage
from utils.pricing import estimate_text_cost, estimate_embedding_cost, estimate_transcription_cost


def record_openai_usage(
    user_id: int,
    operation_type: str,
    model: str,
    response,
    related_job_id=None,
    related_course_id=None,
):
    """Extract usage from an OpenAI response and save to api_usage. Never raises."""
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        # responses API: input_tokens / output_tokens
        # chat completions API: prompt_tokens / completion_tokens
        input_tokens = (
            getattr(usage, "input_tokens", None)
            or getattr(usage, "prompt_tokens", None)
            or 0
        )
        output_tokens = (
            getattr(usage, "output_tokens", None)
            or getattr(usage, "completion_tokens", None)
            or 0
        )
        total_tokens = getattr(usage, "total_tokens", None) or (input_tokens + output_tokens)

        cost = estimate_text_cost(model, input_tokens, output_tokens)

        save_api_usage(
            user_id=user_id,
            operation_type=operation_type,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            related_job_id=related_job_id,
            related_course_id=related_course_id,
        )
    except Exception:
        pass  # tracking must never break the main operation


def record_embedding_usage(
    user_id: int,
    model: str,
    response,
    related_job_id=None,
    related_course_id=None,
):
    """Extract usage from an embeddings response and save to api_usage. Never raises."""
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        input_tokens = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None) or 0
        cost = estimate_embedding_cost(model, input_tokens)

        save_api_usage(
            user_id=user_id,
            operation_type="embedding",
            model=model,
            input_tokens=input_tokens,
            output_tokens=0,
            total_tokens=input_tokens,
            estimated_cost_usd=cost,
            related_job_id=related_job_id,
            related_course_id=related_course_id,
        )
    except Exception:
        pass


def record_transcription_usage(
    user_id: int,
    model: str,
    duration_minutes: float = 0.0,
    related_job_id=None,
    related_course_id=None,
):
    """Save transcription usage. Duration may be unknown (0) — cost will be 0 with TODO note."""
    try:
        cost = estimate_transcription_cost(model, duration_minutes)
        save_api_usage(
            user_id=user_id,
            operation_type="transcription",
            model=model,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            estimated_cost_usd=cost,
            related_job_id=related_job_id,
            related_course_id=related_course_id,
        )
    except Exception:
        pass
