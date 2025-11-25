import unittest
import asyncio
import json
from shouldisignthis.orchestrator import run_stage_6_comparison_drafter

class TestComparisonDrafter(unittest.TestCase):
    def test_comparison_drafter(self):
        """Tests the Comparison Drafter agent with mock comparison result."""
        
        comparison_result = {
            "better_risk_score": "Contract B",
            "comparison_summary": "Contract B is significantly safer due to standard terms and balanced liability.",
            "key_differences": [
                {
                    "category": "Liability",
                    "contract_a_observation": "Unlimited liability.",
                    "contract_b_observation": "Capped at 12 months fees.",
                    "risk_assessment": "Contract A poses catastrophic risk."
                }
            ]
        }
        
        print("\n📧 Testing Comparison Drafter...")
        email_toolkit = asyncio.run(run_stage_6_comparison_drafter("test_user", "test_session", comparison_result))
        
        print(f"📝 Result: {json.dumps(email_toolkit, indent=2)}")
        
        self.assertIsNotNone(email_toolkit)
        self.assertIn("email_subject", email_toolkit)
        self.assertIn("email_body", email_toolkit)
        self.assertIn("strategy_notes", email_toolkit)

if __name__ == "__main__":
    unittest.main()
