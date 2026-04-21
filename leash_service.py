import os
import json
import httpx
import logging

logger = logging.getLogger(__name__)

LEASH_URL = os.getenv(
    "LEASH_URL",
    "https://kvyoe6hbjzq4xfdzcntu5qxxb40jtgiw.lambda-url.us-east-2.on.aws/",
)
LEASH_TIMEOUT = float(os.getenv("LEASH_TIMEOUT", "900"))
LEASH_API_KEY = os.getenv("LEASH_API_KEY", "")

logger.info("[LEASH] API key loaded: %s", LEASH_API_KEY[:8] + "..." if LEASH_API_KEY else "NOT SET")


def _build_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if LEASH_API_KEY:
        headers["x-haig-api-key"] = LEASH_API_KEY
    return headers


async def _post(client: httpx.AsyncClient, body: dict) -> dict:
    logger.info("Leash >>> %s", json.dumps(body, indent=2))
    response = await client.post(LEASH_URL, json=body, headers=_build_headers())
    if not response.is_success:
        logger.error("Leash error %s: %s", response.status_code, response.text)
        raise ValueError(f"Leash {response.status_code}: {response.text[:500]}")
    data = response.json()
    logger.info("Leash <<< %s", json.dumps(data, indent=2))
    return data


async def start_assessment(intake_data: dict) -> dict:
    """Call start, return questions if triage needed, else run full assessment."""
    async with httpx.AsyncClient(timeout=LEASH_TIMEOUT) as client:
        result = await _post(client, {"action": "start", **intake_data})
        return result


async def continue_assessment(session_id: str, answers: list) -> dict:
    """Submit one round of answers and return the raw Leash response (questions or proceed)."""
    async with httpx.AsyncClient(timeout=LEASH_TIMEOUT) as client:
        result = await _post(client, {
            "action": "answer",
            "session_id": session_id,
            "answers": answers,
        })
        return result


async def finish_assessment(session_id: str) -> dict:
    """Run audit + generate after all question rounds are done."""
    async with httpx.AsyncClient(timeout=LEASH_TIMEOUT) as client:
        result = await _post(client, {"action": "audit", "session_id": session_id})
        session_id = result.get("session_id", session_id)
        result = await _post(client, {"action": "generate", "session_id": session_id})
        return result


async def run_assessment(intake_data: dict) -> dict:
    async with httpx.AsyncClient(timeout=LEASH_TIMEOUT) as client:
        session_id = None

        # Step 1 — start
        result = await _post(client, {"action": "start", **intake_data})
        session_id = result.get("session_id", session_id)

        # Step 2 — answer triage questions if required (up to 4 rounds)
        for _ in range(4):
            if result.get("action_required") != "answer_questions":
                break
            questions = result.get("questions", [])
            answers = [
                {"question_index": i, "answer": "Not currently implemented. No documentation exists."}
                for i, _ in enumerate(questions)
            ]
            result = await _post(client, {
                "action": "answer",
                "session_id": session_id,
                "answers": answers,
            })
            session_id = result.get("session_id", session_id)

        # Step 3 — run audit
        result = await _post(client, {"action": "audit", "session_id": session_id})
        session_id = result.get("session_id", session_id)

        # Step 4 — generate report
        result = await _post(client, {"action": "generate", "session_id": session_id})

        return result
