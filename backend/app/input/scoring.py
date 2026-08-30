import re
import logging
from app.input.detectors import harm_intent_detector

logger = logging.getLogger(__name__)

class ComplexityScorer:
    async def score(self, text: str) -> float:
        semantic_score = 0.0
        
        # 1. Semantic Basis using zero-shot classification (fast & semantically robust)
        if harm_intent_detector.is_installed and harm_intent_detector.classifier is not None:
            try:
                import asyncio
                labels = [
                    'complex mathematics, advanced coding, deep reasoning, or theoretical proof',
                    'simple chat, basic question, or short command'
                ]
                
                # Run the synchronous pipeline in a thread
                res = await asyncio.to_thread(
                    harm_intent_detector.classifier, 
                    text[:1000], 
                    labels
                )
                
                complex_label = labels[0]
                complex_idx = res['labels'].index(complex_label)
                prob = res['scores'][complex_idx]
                
                # Scale up probability a bit to hit the 0.75+ threshold for highly complex queries
                semantic_score = min(prob * 1.3, 1.0)
            except Exception as e:
                logger.warning(f"Semantic complexity check failed: {e}")

        # 2. Heuristics fallback / additive components
        heuristic_score = 0.0
        text_lower = text.lower()
        
        # 1. Task length (up to 0.3)
        length = len(text)
        if length > 1000:
            heuristic_score += 0.3
        elif length > 500:
            heuristic_score += 0.2
        elif length > 100:
            heuristic_score += 0.1
            
        # 2. Reasoning markers (up to 0.3)
        reasoning_keywords = ["analyze", "compare", "evaluate", "synthesize", "why", "how", "reason", "step by step", "prove", "solve"]
        matches = sum(1 for kw in reasoning_keywords if kw in text_lower)
        if matches >= 3:
            heuristic_score += 0.3
        elif matches >= 1:
            heuristic_score += 0.15
            
        # 3. Domain specific markers (up to 0.2)
        domain_keywords = ["code", "python", "algorithm", "architecture", "mathematics", "equation", "legal", "medical", "hypothesis", "theorem"]
        domain_matches = sum(1 for kw in domain_keywords if kw in text_lower)
        if domain_matches >= 2:
            heuristic_score += 0.2
        elif domain_matches == 1:
            heuristic_score += 0.1
            
        # 4. Output formatting constraints (up to 0.2)
        format_keywords = ["json", "csv", "table", "markdown", "format", "xml", "yaml"]
        format_matches = sum(1 for kw in format_keywords if kw in text_lower)
        if format_matches >= 2:
            heuristic_score += 0.2
        elif format_matches == 1:
            heuristic_score += 0.1
            
        final_score = max(semantic_score, min(heuristic_score, 1.0))
        return final_score

class TokenBudgetManager:
    def check_budget(self, user_id: str, tokens: int, complexity: float) -> bool:
        # Higher complexity allows larger budget, just a mock logic for now
        budget = 1000 + int(complexity * 4000)
        return tokens <= budget

    def get_max_tokens_for_complexity(self, complexity: float) -> int | None:
        if complexity < 0.25:
            return 256 # LOW
        elif complexity < 0.50:
            return 512 # MEDIUM
        elif complexity < 0.75:
            return 1024 # HIGH
        else:
            return None # NO LIMIT

complexity_scorer = ComplexityScorer()
budget_manager = TokenBudgetManager()
