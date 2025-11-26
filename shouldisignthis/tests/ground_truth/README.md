# Ground Truth Testing System

This directory contains baseline outputs from the contract analysis pipeline for regression testing.

## Structure

Each contract has its own subdirectory containing:
- `auditor_output.json` - Stage 1: Document validation and extraction
- `skeptic_risks.json` - Stage 2a: Risk identification
- `advocate_defense.json` - Stage 2b: Counter-arguments
- `validated_evidence.json` - Stage 2.5: Fact-checked arguments
- `final_verdict.json` - Stage 3: Final decision and score
- `metadata.json` - Capture timestamp and baseline scores

## LLM-Based Validation

This system uses **Gemini 2.5 Pro** to semantically compare new test outputs against these baselines.

### Why LLM Comparison?
- **Semantic Understanding**: LLMs can detect meaningful changes vs. superficial rewording
- **Flexible Tolerance**: Understands that "14 days" and "two weeks" are equivalent
- **Natural Language Feedback**: Provides human-readable explanations of deviations

### Approval Criteria
The LLM comparator **APPROVES** if:
- Verdicts match (ACCEPT/REJECT/CAUTION)
- Risk scores differ by ≤5 points
- Number of risks/counters differ by ≤1
- Content is semantically equivalent (rewording is OK)

The LLM comparator **REJECTS** if:
- Verdict changed
- Risk score differs by >10 points
- Critical fields missing
- Meaning/substance changed significantly

## Usage

### Capturing New Baselines
```bash
# Capture all sample contracts
python shouldisignthis/tests/capture_ground_truth.py --all

# Recapture specific contract
python shouldisignthis/tests/capture_ground_truth.py --contract perfect_contract
```

### Running Validation Tests
```bash
# Test all contracts
pytest shouldisignthis/tests/test_ground_truth.py -v

# Test specific contract
pytest shouldisignthis/tests/test_ground_truth.py::test_ground_truth[perfect_contract] -v

# Show detailed LLM reasoning
pytest shouldisignthis/tests/test_ground_truth.py -v -s
```

## When to Recapture

Recapture ground truth when:
- ✅ Agent instructions are intentionally modified
- ✅ Calculator logic is updated
- ✅ Model versions are upgraded (after manual validation)

Do NOT recapture for:
- ❌ Bug fixes in non-agent code
- ❌ UI changes
- ❌ Documentation updates
- ❌ Minor prompt tweaks (test first to see if LLM approves)

## Example Workflow

1. Make code changes
2. Run `pytest shouldisignthis/tests/test_ground_truth.py -v`
3. If tests fail:
   - Check LLM reasoning in output
   - If deviation is unintended: fix the code
   - If deviation is intentional: recapture baseline
4. Commit both code and ground truth together

## Notes

- Ground truth files are committed to the repository
- LLM comparison requires `GEMINI_API_KEY` environment variable
- Tests are parameterized - one test per contract
- LLM uses temperature=0 for deterministic validation
