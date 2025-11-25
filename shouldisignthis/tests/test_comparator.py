import unittest
import asyncio
import json
from shouldisignthis.orchestrator import run_stage_5_comparator
from shouldisignthis.config import get_judge_model

class TestComparator(unittest.TestCase):
    def test_comparator_logic(self):
        """Tests the Comparator agent with mock verdicts."""
        
        verdict_a = {
            "verdict": "CAUTION",
            "risk_score": 65,
            "summary": "Standard lease but missing late fee clause."
        }
        
        verdict_b = {
            "verdict": "ACCEPT",
            "risk_score": 20,
            "summary": "Very favorable terms for the tenant."
        }
        
        print("\n🥊 Testing Comparator Agent...")
        result = asyncio.run(run_stage_5_comparator("test_user", "test_session", verdict_a, verdict_b))
        
        print(f"🏆 Result: {json.dumps(result, indent=2)}")
        
        self.assertIsNotNone(result)
        self.assertIn("better_risk_score", result)
        self.assertIn("Contract B", result["better_risk_score"]) # B should have better score

if __name__ == "__main__":
    unittest.main()
