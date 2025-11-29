"""
Ground Truth Regression Tests

Pytest-based validation that compares new pipeline runs against ground truth baselines
using LLM-based semantic comparison via Gemini 2.5 Pro.

Usage:
    # Run all ground truth tests
    pytest shouldisignthis/tests/test_ground_truth.py -v
    
    # Run for specific contract
    pytest shouldisignthis/tests/test_ground_truth.py::test_ground_truth[perfect_contract] -v
    
    # Run with detailed output
    pytest shouldisignthis/tests/test_ground_truth.py -v -s
"""

import asyncio
import os
import sys
import json
import uuid
import pytest
from pathlib import Path

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shouldisignthis.config import configure_logging
from shouldisignthis.orchestrator import (
    run_stage_1, 
    run_stage_2, 
    run_stage_2_5, 
    run_stage_3,
    parse_json
)
from shouldisignthis.tests.utils.llm_comparator import (
    AgentGroundTruthComparator,
    format_comparison_report
)

from datetime import datetime

import yaml
import shouldisignthis.config as app_config
from google.genai import types

configure_logging()

@pytest.fixture(scope="module", autouse=True)
def setup_ground_truth_config():
    """
    Patches the app configuration to use ground_truth_config.yaml for these tests.
    """
    # 1. Load GT Config
    gt_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ground_truth_config.yaml"))
    with open(gt_config_path, "r") as f:
        gt_config = yaml.safe_load(f)
        
    # 2. Backup original
    original_config = app_config.APP_CONFIG.copy()
    
    # 3. Patch
    app_config.APP_CONFIG.clear()
    app_config.APP_CONFIG.update(gt_config)
    
    # 4. Update dependents
    app_config.models_cfg = app_config.APP_CONFIG.get("models", {})
    app_config.SAFE_CONTRACT_SETTINGS = app_config.APP_CONFIG.get("safety_settings", {})
    app_config.RETRY_POLICY = types.HttpRetryOptions(
        attempts=app_config.APP_CONFIG.get("retry_policy", {}).get("attempts", 5),
        exp_base=app_config.APP_CONFIG.get("retry_policy", {}).get("exp_base", 2),
        initial_delay=app_config.APP_CONFIG.get("retry_policy", {}).get("initial_delay", 1),
        http_status_codes=app_config.APP_CONFIG.get("retry_policy", {}).get("http_status_codes", [429, 500, 503])
    )
    
    # 5. Re-configure logging
    app_config.configure_logging(log_file_override="ground_truth.log")
    
    yield
    
    # 6. Restore
    app_config.APP_CONFIG.clear()
    app_config.APP_CONFIG.update(original_config)
    app_config.models_cfg = app_config.APP_CONFIG.get("models", {})
    app_config.SAFE_CONTRACT_SETTINGS = app_config.APP_CONFIG.get("safety_settings", {})
    # Note: We don't strictly need to restore logging as the process will exit, 
    # but good practice if we were running more tests in the same session.

SAMPLE_CONTRACTS_DIR = Path(__file__).parent / "sample_contracts"
GROUND_TRUTH_DIR = Path(__file__).parent / "ground_truth"
REPORT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "test_output" / "ground_truth_reports"
TEST_OUTPUT_DIR = Path(__file__).parent.parent.parent / "test_output" / "ground_truth"

# Global to collect test results for PDF report
_test_results = {
    "timestamp": datetime.now().isoformat(),
    "total_contracts": 0,
    "passed": 0,
    "failed": 0,
    "contracts": {}
}


def save_test_outputs(contract_name: str, outputs: dict, stage: str = None):
    """
    Save test run outputs to test_output directory for easy comparison.
    
    This allows users to review new outputs and easily replace ground truth
    baselines if the changes are intentional.
    
    Args:
        contract_name: Name of the contract
        outputs: Dictionary of outputs to save
        stage: Optional stage name to save only that stage
    """
    output_dir = TEST_OUTPUT_DIR / contract_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save each stage output
    stage_files = {
        "auditor": "auditor_output.json",
        "skeptic": "skeptic_risks.json",
        "advocate": "advocate_defense.json",
        "bailiff": "validated_evidence.json",
        "verdict": "final_verdict.json"
    }
    
    if stage:
        # Save only the specified stage
        if stage in stage_files and stage in outputs:
            with open(output_dir / stage_files[stage], 'w') as f:
                json.dump(outputs[stage], f, indent=2)
    else:
        # Save all available stages
        for stage_name, filename in stage_files.items():
            if stage_name in outputs:
                with open(output_dir / filename, 'w') as f:
                    json.dump(outputs[stage_name], f, indent=2)
    
    # Save metadata
    metadata = {
        "contract_name": contract_name,
        "test_run_timestamp": datetime.now().isoformat(),
        "purpose": "Test run output for comparison with ground truth",
        "note": "To update ground truth, copy these files to shouldisignthis/tests/ground_truth/{contract_name}/",
        "last_stage_tested": stage
    }
    
    with open(output_dir / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  💾 Test outputs saved to: {output_dir}")


def get_ground_truth_contracts():
    """Get list of contracts that have ground truth baselines."""
    if not GROUND_TRUTH_DIR.exists():
        return []
    
    contracts = []
    
    contracts = []
    
    # Check for config filter directly from file since fixture hasn't run yet
    gt_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ground_truth_config.yaml"))
    config_contracts = []
    try:
        with open(gt_config_path, "r") as f:
            gt_cfg = yaml.safe_load(f)
            config_contracts = gt_cfg.get("ground_truth", {}).get("contracts", [])
    except Exception:
        pass
    
    for contract_dir in GROUND_TRUTH_DIR.iterdir():
        if contract_dir.is_dir():
            # Check if it has metadata.json
            if (contract_dir / "metadata.json").exists():
                contract_name = contract_dir.name
                
                # Apply filter if configured
                if config_contracts and contract_name not in config_contracts:
                    continue
                    
                contracts.append(contract_name)
    
    return contracts


@pytest.mark.parametrize("contract_name", get_ground_truth_contracts())
@pytest.mark.asyncio
async def test_ground_truth(contract_name):
    """
    Test a contract against its ground truth baseline using LLM comparison.
    
    Runs the pipeline sequentially and validates each stage against ground truth.
    Stops execution immediately if a stage fails.
    
    Args:
        contract_name: Name of the contract (without .pdf extension)
    """
    print(f"\n{'='*70}")
    print(f"Testing: {contract_name}")
    print(f"{'='*70}")
    
    comparator = AgentGroundTruthComparator()
    ground_truth_path = GROUND_TRUTH_DIR / contract_name
    
    # Initialize pipeline state
    pdf_path = SAMPLE_CONTRACTS_DIR / f"{contract_name}.pdf"
    if not pdf_path.exists():
        pytest.fail(f"Contract PDF not found: {pdf_path}")
        
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
        
    user_id = f"test_user_{uuid.uuid4()}"
    session_id = str(uuid.uuid4())
    
    # Track outputs for saving
    current_outputs = {}
    
    # Track validation results
    validation_summary = {
        "contract": contract_name,
        "status": "PASSED",
        "stages": {}
    }

    async def validate_stage(stage_name: str, output_data: dict, filename: str):
        """Validate a stage's output against ground truth."""
        print(f"\n🔍 Comparing stage '{stage_name}' with ground truth...")
        
        # Save current output first
        current_outputs[stage_name] = output_data
        save_test_outputs(contract_name, current_outputs, stage=stage_name)
        
        gt_file = ground_truth_path / filename
        if not gt_file.exists():
            pytest.fail(
                f"\n❌ GROUND TRUTH FILE MISSING\n"
                f"Expected: {gt_file}\n"
                f"Run: python shouldisignthis/tests/capture_ground_truth.py --contract {contract_name}"
            )
            
        with open(gt_file, 'r') as f:
            ground_truth = json.load(f)
            
        # Compare using agent
        print(f"  🤖 Agent validating: {stage_name}...")
        result = await comparator.compare_outputs(stage_name, ground_truth, output_data)
        
        # Record result
        validation_summary["stages"][stage_name] = {
            "approved": result.approved,
            "reason": result.reason,
            "deviation": result.deviation_details
        }
        
        # Save summary incrementally
        summary_path = TEST_OUTPUT_DIR / contract_name / "validation_summary.json"
        with open(summary_path, "w") as f:
            json.dump(validation_summary, f, indent=2)
        
        # Show result
        print(f"\n{result.get_report()}")
        
        if not result.approved:
            validation_summary["status"] = "FAILED"
            validation_summary["failed_stage"] = stage_name
            with open(summary_path, "w") as f:
                json.dump(validation_summary, f, indent=2)

            new_output_path = TEST_OUTPUT_DIR / contract_name / filename
            gt_output_path = ground_truth_path / filename
            
            print(f"\n{'='*70}")
            print(f"❌ FAILURE DETECTED - STOPPING EXECUTION")
            print(f"{'='*70}")
            print(f"\nStage '{stage_name}' failed validation.")
            print(f"\nReason: {result.reason}")
            if result.deviation_details:
                print(f"\nDeviation Details:\n{result.deviation_details}")
            if result.suggested_fix:
                print(f"\n💡 Suggested Fix:\n{result.suggested_fix}")
            
            print(f"\n📁 Compare files manually:")
            print(f"   Ground Truth:  {gt_output_path}")
            print(f"   New Output:    {new_output_path}")
            
            pytest.fail(
                f"Ground truth validation failed at stage '{stage_name}'\n"
                f"Reason: {result.reason}"
            )
            
        print(f"  ✅ Stage '{stage_name}' passed validation")

    # --- Stage 1: Auditor ---
    print(f"\n[Stage 1/5] Running Auditor...")
    auditor_out = await run_stage_1(pdf_bytes, "application/pdf", user_id, session_id)
    await validate_stage("auditor", auditor_out, "auditor_output.json")
    
    # Check for rejection
    if not auditor_out.get("is_contract") or auditor_out.get("is_safe") is False:
        print(f"\n⚠️ Contract rejected by auditor. Validation complete.")
        # We should also validate the rejection verdict if it exists in ground truth
        # But for now, we assume if auditor matches, we are good.
        return

    fact_sheet = auditor_out.get("fact_sheet")
    full_text = auditor_out.get("full_text")

    # --- Stage 2: Debate ---
    print(f"\n[Stage 2/5] Running Debate Team (Skeptic + Advocate)...")
    stage2_state, _ = await run_stage_2(user_id, session_id, fact_sheet)
    
    skeptic_risks = parse_json(stage2_state.get('skeptic_risks'))
    advocate_defense = parse_json(stage2_state.get('advocate_defense'))
    
    await validate_stage("skeptic", skeptic_risks, "skeptic_risks.json")
    await validate_stage("advocate", advocate_defense, "advocate_defense.json")

    # --- Stage 2.5: Bailiff ---
    print(f"\n[Stage 3/5] Running Bailiff...")
    risks = skeptic_risks.get('risks', [])
    counters = advocate_defense.get('counters', [])
    validated_evidence = await run_stage_2_5(user_id, session_id, risks, counters, full_text)
    
    await validate_stage("bailiff", validated_evidence, "validated_evidence.json")

    # --- Stage 3: Judge ---
    print(f"\n[Stage 4/5] Running Judge...")
    verdict = await run_stage_3(user_id, session_id, fact_sheet, validated_evidence)
    
    await validate_stage("verdict", verdict, "final_verdict.json")

    # --- Success ---
    print(f"\n{'='*70}")
    print(f"✅ ALL STAGES PASSED for {contract_name}")
    print(f"{'='*70}\n")
    
    _test_results["total_contracts"] += 1
    _test_results["passed"] += 1
    _test_results["contracts"][contract_name] = {
        "status": "PASSED",
        "stages": {"all": {"approved": True}}
    }


@pytest.mark.asyncio
async def test_ground_truth_exists():
    """Verify that ground truth baselines exist."""
    if not GROUND_TRUTH_DIR.exists():
        pytest.fail(
            f"Ground truth directory not found: {GROUND_TRUTH_DIR}\n"
            "Run `python shouldisignthis/tests/capture_ground_truth.py --all` to capture baselines."
        )
    
    contracts = get_ground_truth_contracts()
    if not contracts:
        pytest.fail(
            "No ground truth baselines found.\n"
            "Run `python shouldisignthis/tests/capture_ground_truth.py --all` to capture baselines."
        )
    
    print(f"\n✅ Found {len(contracts)} ground truth baseline(s):")
    for contract in contracts:
        print(f"  • {contract}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
