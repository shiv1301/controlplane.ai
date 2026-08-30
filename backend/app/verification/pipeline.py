import logging
import json
from app.routing.router import router as llm_router
from app.verification.retriever import retriever
from app.verification.nli import nli_verifier
from app.database.session import AsyncSessionLocal
from app.database.models import VerificationLog
from app.observability.metrics import VERIFICATION_RESULTS

logger = logging.getLogger(__name__)

class ClaimExtractor:
    async def extract(self, text: str) -> list[str]:
        """Uses qwen3:1.7b to extract factual claims from text."""
        provider = llm_router.get_provider_for_model("qwen3:1.7b")
        prompt = (
            "Extract distinct factual claims from the following text. "
            "Output strictly a JSON array of strings, with no markdown formatting or other text.\n"
            f"Text: {text}"
        )
        
        try:
            response = await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                model="qwen3:1.7b",
                temperature=0.1
            )
            content = response.get("message", {}).get("content", "").strip()
            
            # Simple heuristic to strip markdown backticks if the model ignores the instruction
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            claims = json.loads(content.strip())
            if isinstance(claims, list):
                return claims
            raise ValueError("Claim extraction did not return a list")
        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            raise RuntimeError(f"Verification Unavailable: {e}")

class VerificationPipeline:
    def __init__(self):
        self.extractor = ClaimExtractor()
        
    async def verify_text(self, request_id: str, text: str, attempt: int = 0) -> dict:
        """
        Returns:
        {
            "is_valid": bool, # True if no CONTRADICTED claims
            "contradicted_claims": list[str],
            "unsupported_claims": list[str],
            "supported_claims": list[str]
        }
        """
        try:
            claims = await self.extractor.extract(text)
        except Exception as e:
            # FAIL CLOSED
            return {
                "is_valid": False, 
                "contradicted_claims": ["SYSTEM_VERIFICATION_FAILURE"], 
                "unsupported_claims": [], 
                "supported_claims": []
            }
            
        if not claims:
            return {"is_valid": True, "contradicted_claims": [], "unsupported_claims": [], "supported_claims": []}
            
        supported = []
        unsupported = []
        contradicted = []
        
        for claim in claims:
            # Retrieve evidence
            top_docs = await retriever.retrieve(claim, top_k=2)
            evidence = " ".join(top_docs)
            
            # Verify
            nli_res = nli_verifier.verify(claim, evidence)
            result = nli_res['result']
            score = nli_res['score']
            VERIFICATION_RESULTS.labels(result_type=result).inc()
            
            # Log it
            async with AsyncSessionLocal() as session:
                log_entry = VerificationLog(
                    request_id=request_id,
                    claim_text=claim,
                    evidence_text=evidence,
                    nli_result=result,
                    nli_score=score,
                    regeneration_attempt=attempt
                )
                session.add(log_entry)
                await session.commit()
                
            if result == "SUPPORTED":
                supported.append(claim)
            elif result == "CONTRADICTED":
                contradicted.append(claim)
            else:
                unsupported.append(claim)
                
        # We consider a text invalid if it has CONTRADICTED claims.
        # Unsupported is typically just a warning, but for strictness we track it.
        return {
            "is_valid": len(contradicted) == 0,
            "contradicted_claims": contradicted,
            "unsupported_claims": unsupported,
            "supported_claims": supported
        }

verification_pipeline = VerificationPipeline()

