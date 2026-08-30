import pytest
from unittest.mock import patch, AsyncMock
from app.verification.lazy_models import lazy_loader
from app.verification.retriever import retriever
from app.verification.nli import nli_verifier
from app.verification.pipeline import verification_pipeline
from app.verification.mock_kb import seed_mock_kb

@pytest.mark.asyncio
async def test_retriever_hybrid_and_reranking():
    await seed_mock_kb()
    
    # "The Control Plane AI is designed to inspect traffic and enforce policies." is in the DB
    results = await retriever.retrieve("What is Control Plane AI designed for?", top_k=1)
    
    assert len(results) == 1
    assert "inspect traffic" in results[0]

def test_nli_verifier_supported():
    claim = "Microservices prioritize flexibility."
    evidence = "Microservices architecture prioritizes flexibility and independent deployment."
    
    res = nli_verifier.verify(claim, evidence)
    assert res["result"] == "SUPPORTED"
    
def test_nli_verifier_contradicted():
    claim = "Python is perfectly parallel natively without multiprocessing."
    evidence = "Python is single-threaded due to the GIL, making CPU-bound scaling difficult without multiprocessing."
    
    res = nli_verifier.verify(claim, evidence)
    assert res["result"] == "CONTRADICTED"

@pytest.mark.asyncio
async def test_lazy_loading_unloading():
    # Load model
    encoder = lazy_loader.get_cross_encoder("BAAI/bge-reranker-v2-m3")
    assert encoder is not None
    # Unload model
    lazy_loader.unload("BAAI/bge-reranker-v2-m3")
    assert "BAAI/bge-reranker-v2-m3" not in lazy_loader._models

@pytest.mark.asyncio
async def test_verification_pipeline_regeneration_limit():
    # If a text generates claims that are contradictory, the pipeline flags it as invalid
    with patch('app.verification.pipeline.ClaimExtractor.extract', new_callable=AsyncMock) as mock_ext:
        mock_ext.return_value = ["Python is perfectly parallel natively without multiprocessing."]
        
        # Test attempt 0
        v_res = await verification_pipeline.verify_text("req-123", "Some fake response", attempt=0)
        
        assert v_res["is_valid"] is False
        assert len(v_res["contradicted_claims"]) > 0

@pytest.mark.asyncio
async def test_nli_failure_safe_behavior():
    # If NLI model is unloaded and throws exception, it must fail safely to UNSUPPORTED
    with patch.object(lazy_loader, 'get_pipeline', return_value=None):
        res = nli_verifier.verify("Test claim", "Test evidence")
        assert res["result"] == "UNSUPPORTED"

