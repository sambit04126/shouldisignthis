import os
import json
import glob
from pathlib import Path
from datetime import datetime
import yaml

# Paths
TEST_OUTPUT_DIR = Path(__file__).parent.parent.parent / "test_output" / "ground_truth"
CONFIG_PATH = Path(__file__).parent.parent / "ground_truth_config.yaml"

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return {}

def generate_report():
    print("📊 Generating Ground Truth Report...")
    
    if not TEST_OUTPUT_DIR.exists():
        print("❌ No test output found.")
        return

    config = load_config()
    model_name = config.get("models", {}).get("judge", "Unknown")
    
    report_lines = []
    report_lines.append(f"# Ground Truth Report")
    report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Model:** {model_name}")
    report_lines.append("")
    report_lines.append("| Contract | Auditor Verdict | Judge Verdict | Validation Status | Details |")
    report_lines.append("| :--- | :--- | :--- | :--- | :--- |")

    # Iterate through contract directories
    for contract_dir in sorted(TEST_OUTPUT_DIR.iterdir()):
        if not contract_dir.is_dir():
            continue
            
        contract_name = contract_dir.name
        metadata_path = contract_dir / "metadata.json"
        
        if not metadata_path.exists():
            continue
            
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            
        timestamp = metadata.get("test_run_timestamp", "N/A")
        
        # Check for stage files to determine what ran
        stages = ["auditor", "skeptic", "advocate", "bailiff", "verdict"]
        
        for stage in stages:
            # Logic to determine pass/fail would ideally come from a results file
            # Since we don't have a centralized results file yet, we'll infer from existence 
            # and potentially a 'validation_results.json' if we added that.
            # For now, let's list the stages found.
            
            # TODO: Enhance test runner to save a 'validation_summary.json' in the output dir
            # For now, we will just list the contract and timestamp.
            pass

    # REVISED APPROACH:
    # The current test runner prints results but doesn't save a structured summary of the *validation* itself (Pass/Fail).
    # It only saves the *outputs*.
    # To get the "Verdict of LLM Judge", we need to read the output files.
    
    for contract_dir in sorted(TEST_OUTPUT_DIR.iterdir()):
        if not contract_dir.is_dir():
            continue
        
        contract_name = contract_dir.name
        
        # 1. Read Validation Summary
        summary_file = contract_dir / "validation_summary.json"
        validation_status = "❓ Unknown"
        failure_details = "-"
        
        if summary_file.exists():
            try:
                with open(summary_file) as f:
                    summary = json.load(f)
                    status = summary.get("status", "UNKNOWN")
                    if status == "PASSED":
                        validation_status = "✅ PASS"
                    elif status == "FAILED":
                        validation_status = "❌ FAIL"
                        failed_stage = summary.get("failed_stage", "Unknown")
                        reason = summary.get("stages", {}).get(failed_stage, {}).get("reason", "No reason")
                        failure_details = f"Failed at **{failed_stage}**: {reason}"
            except Exception:
                pass
        
        # 2. Auditor Verdict
        auditor_verdict = "N/A"
        auditor_file = contract_dir / "auditor_output.json"
        if auditor_file.exists():
            with open(auditor_file) as f:
                data = json.load(f)
                auditor_verdict = "Safe" if data.get("is_safe") else "Unsafe"
        
        # 3. Judge Verdict
        judge_verdict = "N/A"
        judge_file = contract_dir / "final_verdict.json"
        if judge_file.exists():
            with open(judge_file) as f:
                data = json.load(f)
                judge_verdict = f"{data.get('verdict')} ({data.get('risk_score')})"

        report_lines.append(f"| {contract_name} | {auditor_verdict} | {judge_verdict} | {validation_status} | {failure_details} |")

    output_file = TEST_OUTPUT_DIR / "ground_truth_report.md"
    with open(output_file, "w") as f:
        f.write("\n".join(report_lines))
        
    print(f"✅ Report saved to: {output_file}")
    print("\n".join(report_lines))

if __name__ == "__main__":
    generate_report()
