"""
LLM Comparator for Ground Truth Testing
"""
import json
import uuid
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Optional

from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from shouldisignthis.agents.ground_truth_validator import get_ground_truth_validator_agent

@dataclass
class ComparisonResult:
    approved: bool
    reason: str
    deviation_details: str = ""
    suggested_fix: str = ""
    
    def get_report(self) -> str:
        status = "✅ APPROVED" if self.approved else "❌ REJECTED"
        report = [
            f"Status: {status}",
            f"Reason: {self.reason}"
        ]
        if self.deviation_details:
            report.append(f"Deviations: {self.deviation_details}")
        if self.suggested_fix:
            report.append(f"Fix: {self.suggested_fix}")
        return "\n".join(report)


class AgentGroundTruthComparator:
    def __init__(self):
        pass
        
    async def compare_outputs(self, stage: str, ground_truth: Dict[str, Any], new_output: Dict[str, Any]) -> ComparisonResult:
        """
        Compare ground truth with new output using the validator agent.
        """
        # Create a fresh agent instance for each run
        agent = get_ground_truth_validator_agent()
        
        # Prepare the prompt input
        user_message = (
            f"STAGE: {stage}\n\n"
            f"--- GROUND TRUTH ---\n"
            f"{json.dumps(ground_truth, indent=2)}\n\n"
            f"--- NEW TEST OUTPUT ---\n"
            f"{json.dumps(new_output, indent=2)}"
        )
        
        # Run the agent using ADK Runner
        # Use InMemorySessionService to avoid DB conflicts and session lookup issues
        session_service = InMemorySessionService()
        
        # The ADK Runner might override app_name based on the agent's module if there's a mismatch.
        # We'll use "agents" to be safe, as suggested by previous error logs.
        app_name = "agents"
        app = App(name=app_name, root_agent=agent)
        runner = Runner(app=app, session_service=session_service)
        
        user_id = "test_comparator"
        session_id = str(uuid.uuid4())
        
        # Explicitly create session to ensure it exists
        await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
        
        msg = types.Content(role="user", parts=[types.Part(text=user_message)])
        
        try:
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
                pass
                
            session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
            
            # The agent is configured to store output in 'validation_result'
            # But sometimes it might be in the last message if state update failed
            # However, LlmAgent usually updates state if output_key is set.
            
            response_content = session.state.get('validation_result')
            
            # If response_content is a string (JSON string), parse it
            if isinstance(response_content, str):
                content = response_content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                result_json = json.loads(content)
            elif isinstance(response_content, dict):
                result_json = response_content
            else:
                return ComparisonResult(
                    approved=False,
                    reason="No valid output from validator agent",
                    deviation_details=f"State: {session.state}"
                )
            
            decision = result_json.get("decision", "REJECT")
            approved = decision == "APPROVE"
            
            return ComparisonResult(
                approved=approved,
                reason=result_json.get("reason", "No reason provided"),
                deviation_details=result_json.get("deviation_summary", ""),
                suggested_fix=result_json.get("suggested_fix", "")
            )
            
        except json.JSONDecodeError:
            return ComparisonResult(
                approved=False,
                reason="Failed to parse validator agent response",
                deviation_details=f"Raw response: {response_content}"
            )
        except Exception as e:
            return ComparisonResult(
                approved=False,
                reason=f"Error during validation: {str(e)}",
                deviation_details=str(e)
            )
        finally:
            # Cleanup session
            try:
                await session_service.delete_session(app_name=app_name, user_id=user_id, session_id=session_id)
            except:
                pass

def format_comparison_report(result: ComparisonResult) -> str:
    return result.get_report()
