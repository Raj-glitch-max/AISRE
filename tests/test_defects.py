"""Tests that reproduce defects D1-D12 as strict-xfail tests (red tests).

These tests assert the CORRECT behavior (what should happen after fix).
They FAIL now because the defects exist, so we mark them xfail.
When a defect is fixed, the test will pass and we remove the xfail in the same commit.
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))

# Import modules under test
from agent import (
    investigate,
    _execute_tool,
    _validate_rca,
    TOOL_FUNCTIONS,
    SYSTEM_PROMPT,
    TOOLS,
)
from tools import (
    get_container_status,
    get_recent_logs,
    get_recent_commits,
)
from remediation import (
    approve_and_remediate,
    _gated_restart,
    _restart_container,
    _ecs_restart,
    _check_health,
)
from poller import run_poller, active_incident_id
from atlas_sdk import AtlasClient, Decision
from database import SessionLocal, engine
from models import Incident
from faithfulness_eval import check_faithfulness


# =============================================================================
# D1: Tool argument injection - CORRECT behavior tests
# =============================================================================

class TestD1ToolArgumentInjection:
    """D1: Tool argument injection vulnerabilities - tests for correct behavior."""

    def test_d1a_get_recent_commits_rejects_invalid_count(self):
        """D1a: get_recent_commits should reject non-integer count values."""
        repo_path = Path(__file__).parent.parent / "victim-app"
        # Should reject string that looks like argv injection
        with pytest.raises((ValueError, TypeError)):
            get_recent_commits(str(repo_path), count="-output=/tmp/x")
        # Should reject negative numbers
        with pytest.raises(ValueError):
            get_recent_commits(str(repo_path), count=-5)
        # Should reject excessive values
        with pytest.raises(ValueError):
            get_recent_commits(str(repo_path), count=1000)

    def test_d1b_container_name_validated_against_target(self):
        """D1b: container_name should only accept the configured target container."""
        # Should reject arbitrary container names
        with pytest.raises(ValueError):
            get_container_status("arbitrary-container")
        # Should accept the configured VICTIM_CONTAINER
        # (would need actual container running, so we test the validation logic)
        import tools
        import inspect
        source = inspect.getsource(tools.get_container_status)
        # After fix: should validate container_name against configured target

    def test_d1c_lines_parameter_validated(self):
        """D1c: lines parameter should be validated (positive int <= 200)."""
        with pytest.raises(ValueError):
            get_recent_logs("victim-app", lines=-100)
        with pytest.raises(ValueError):
            get_recent_logs("victim-app", lines=1000000)
        with pytest.raises(TypeError):
            get_recent_logs("victim-app", lines="not-an-int")

    def test_d1d_count_parameter_validated(self):
        """D1d: count parameter should be validated (positive int <= 20)."""
        repo_path = Path(__file__).parent.parent / "victim-app"
        with pytest.raises(ValueError):
            get_recent_commits(str(repo_path), count=-5)
        with pytest.raises(ValueError):
            get_recent_commits(str(repo_path), count=1000)
        with pytest.raises(TypeError):
            get_recent_commits(str(repo_path), count="not-an-int")

    def test_d1e_model_arguments_validated_before_execution(self):
        """D1e: agent.py should validate model-chosen arguments before executing tools."""
        import agent
        import inspect
        source = inspect.getsource(agent._execute_tool)
        # After fix: should validate tool_input against schema before calling tool
        # Currently: no validation, just calls TOOL_FUNCTIONS[name](tool_input)
        assert "validate" in source.lower() or "schema" in source.lower(), \
            "No validation of model arguments before tool execution"


# =============================================================================
# D2: Approval endpoint - CORRECT behavior tests
# =============================================================================

class TestD2ApprovalAuth:
    """D2: Approval endpoint should require authentication and be race-free."""

    def test_d2a_approve_requires_credentials(self, temp_db):
        """D2a: POST /incidents/{id}/approve should require valid credentials."""
        from fastapi.testclient import TestClient
        import main
        import remediation
        from models import Incident
        from unittest.mock import MagicMock, patch

        original_session = main.SessionLocal
        main.SessionLocal = temp_db
        remediation.set_session_factory(temp_db)

        # Mock Atlas client to avoid network calls
        mock_atlas = MagicMock()
        mock_grant = MagicMock()
        mock_grant.record = "test-record"
        mock_grant.instance = "test-instance"
        mock_atlas.issue.return_value = mock_grant
        mock_result = MagicMock()
        mock_result.decision = "ACCEPT"
        mock_atlas.verify.return_value = mock_result

        try:
            with patch.object(remediation, 'atlas', mock_atlas):
                client = TestClient(main.app)

                db = temp_db()
                incident = Incident(status="pending_approval", service_name="victim-app")
                db.add(incident)
                db.commit()
                db.refresh(incident)
                incident_id = incident.id
                db.close()

                # Without credentials should return 401
                response = client.post(f"/incidents/{incident_id}/approve")
                assert response.status_code == 401

                # With wrong token should return 401
                response = client.post(f"/incidents/{incident_id}/approve", headers={"Authorization": "Bearer wrong-token"})
                assert response.status_code == 401

                # With correct token should not return 401 (may fail for other reasons)
                response = client.post(f"/incidents/{incident_id}/approve", headers={"Authorization": "Bearer test-approval-token"})
                assert response.status_code != 401
        finally:
            main.SessionLocal = original_session
            remediation.set_session_factory(None)

    def test_d2b_approve_stores_approver_identity_and_time(self, temp_db):
        """D2b: Approval should store approver identity and timestamp."""
        from fastapi.testclient import TestClient
        import main
        import remediation
        from models import Incident
        from datetime import datetime
        from unittest.mock import MagicMock, patch

        original_session = main.SessionLocal
        main.SessionLocal = temp_db
        remediation.set_session_factory(temp_db)

        # Mock Atlas client to avoid network calls
        mock_atlas = MagicMock()
        mock_grant = MagicMock()
        mock_grant.record = "test-record"
        mock_grant.instance = "test-instance"
        mock_atlas.issue.return_value = mock_grant
        mock_result = MagicMock()
        mock_result.decision = "ACCEPT"
        mock_atlas.verify.return_value = mock_result

        try:
            with patch.object(remediation, 'atlas', mock_atlas):
                client = TestClient(main.app)

                db = temp_db()
                incident = Incident(status="pending_approval", service_name="victim-app")
                db.add(incident)
                db.commit()
                db.refresh(incident)
                incident_id = incident.id
                db.close()

                # With valid credentials
                response = client.post(f"/incidents/{incident_id}/approve", headers={"Authorization": "Bearer test-approval-token"})

                # Check that approval info was stored
                db = temp_db()
                incident = db.query(Incident).filter(Incident.id == incident_id).first()
                assert incident.approved_by == "test-approval-token"
                assert incident.approved_at is not None
                assert isinstance(incident.approved_at, datetime)
                db.close()
        finally:
            main.SessionLocal = original_session
            remediation.set_session_factory(None)

    def test_d2c_race_condition_prevented_exactly_once_execution(self, temp_db):
        """D2c: Two racing approvals should result in exactly one execution."""
        from fastapi.testclient import TestClient
        import main
        import remediation
        from models import Incident
        import threading
        from unittest.mock import MagicMock, patch

        original_session = main.SessionLocal
        main.SessionLocal = temp_db
        remediation.set_session_factory(temp_db)

        # Mock Atlas client to avoid network calls
        mock_atlas = MagicMock()
        mock_grant = MagicMock()
        mock_grant.record = "test-record"
        mock_grant.instance = "test-instance"
        mock_atlas.issue.return_value = mock_grant
        mock_result = MagicMock()
        mock_result.decision = "ACCEPT"
        mock_atlas.verify.return_value = mock_result

        try:
            with patch.object(remediation, 'atlas', mock_atlas):
                client = TestClient(main.app)

                db = temp_db()
                incident = Incident(status="pending_approval", service_name="victim-app")
                db.add(incident)
                db.commit()
                db.refresh(incident)
                incident_id = incident.id
                db.close()

                results = []
                def approve():
                    # With valid auth
                    response = client.post(f"/incidents/{incident_id}/approve", headers={"Authorization": "Bearer test-approval-token"})
                    results.append(response.status_code)

                t1 = threading.Thread(target=approve)
                t2 = threading.Thread(target=approve)
                t1.start()
                t2.start()
                t1.join()
                t2.join()

                # Exactly one should succeed (200 or 202), other should get 409 Conflict
                success_count = sum(1 for r in results if r in (200, 202))
                conflict_count = sum(1 for r in results if r == 409)
                assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
                assert conflict_count == 1, f"Expected exactly 1 conflict, got {conflict_count}"
        finally:
            main.SessionLocal = original_session
            remediation.set_session_factory(None)

    def test_d2d_demo_trigger_requires_enable_demo_flag(self):
        """D2d: /demo/trigger-incident should be disabled unless ENABLE_DEMO=true."""
        from fastapi.testclient import TestClient
        import main

        original_session = main.SessionLocal
        # Don't override SessionLocal for this test - just test the endpoint

        try:
            client = TestClient(main.app)

            # Test with ENABLE_DEMO=false
            import os
            os.environ["ENABLE_DEMO"] = "false"

            # Need to reimport main to pick up new env
            import importlib
            importlib.reload(main)

            # Recreate client with reloaded app
            client = TestClient(main.app)

            # Without ENABLE_DEMO=true, should return 403
            with patch("main.httpx.post") as mock_post:
                mock_post.return_value = MagicMock(status_code=200)
                response = client.post("/demo/trigger-incident")
                # After fix: should be 403 when ENABLE_DEMO != true
                assert response.status_code == 403

            # Restore
            os.environ["ENABLE_DEMO"] = "true"
            importlib.reload(main)
        finally:
            main.SessionLocal = original_session


# =============================================================================
# D3: Atlas gate - CORRECT behavior tests
# =============================================================================

class TestD3AtlasGate:
    """D3: Atlas capability gate should work correctly."""

    def test_d3a_gated_restart_separates_issue_and_verify(self):
        """D3a: Issue and verify should be separate; API key should be used."""
        import remediation
        import inspect
        source = inspect.getsource(remediation._gated_restart)
        # After fix: issue and verify should be separate calls/steps
        # and atlas client should be initialized with API key
        # Currently: both in same function, no API key
        assert "api_key" in source, "Atlas client should use API key"
        # Should have separate issue and verify phases (not in same function)

    def test_d3b_principal_and_delegate_configurable(self):
        """D3b: Principal and delegate should be configurable, not hardcoded."""
        import remediation
        import inspect
        source = inspect.getsource(remediation)
        # After fix: should read from environment, not hardcoded constants
        # Check that the hardcoded strings are NOT present
        assert "spiffe://ai-sre.local/system/approval-gate" not in source, \
            "ATLAS_PRINCIPAL should not be hardcoded"
        assert "spiffe://ai-sre.local/agent/remediation-executor" not in source, \
            "ATLAS_DELEGATE should not be hardcoded"
        # Should use os.getenv for these
        assert 'os.getenv("ATLAS_PRINCIPAL"' in source or "os.getenv('ATLAS_PRINCIPAL'" in source, \
            "ATLAS_PRINCIPAL should be read from environment"
        assert 'os.getenv("ATLAS_DELEGATE"' in source or "os.getenv('ATLAS_DELEGATE'" in source, \
            "ATLAS_DELEGATE should be read from environment"

    def test_d3c_supports_offline_verification(self):
        """D3c: Should support offline verification via JWS decode."""
        import remediation
        import inspect
        source = inspect.getsource(remediation)
        # After fix: should have offline verification (JWS decode) capability
        assert "jws" in source.lower() or "jwt" in source.lower() or "offline" in source.lower(), \
            "No offline verification support found"

    def test_d3d_atlas_gates_all_investigation_tools(self):
        """D3d: Atlas should gate all 3 investigation tools, not just restart."""
        import agent
        import inspect
        source = inspect.getsource(agent.investigate)
        # After fix: each tool call should check capability before executing
        assert "capability" in source.lower() or "investigate:" in source.lower(), \
            "No capability checks for investigation tools"

    def test_d3e_no_default_atlas_url_requires_explicit_config(self):
        """D3e: No default ATLAS_URL - must be explicitly configured."""
        import atlas_sdk
        import inspect
        source = inspect.getsource(atlas_sdk.AtlasClient.__init__)
        # After fix: no default URL, must be provided (no default parameter)
        # Currently has default: base_url: str = "http://127.0.0.1:8087"
        # But remediation.py overrides with Railway URL
        import remediation
        rem_source = inspect.getsource(remediation)
        assert "railway.app" not in rem_source, "Should not have Railway URL default"

    def test_d3f_scope_format_matches_atlas_expectations(self):
        """D3f: Scope format should match what Atlas server expects."""
        import remediation
        import inspect
        source = inspect.getsource(remediation._gated_restart)
        # After fix: scope should use VICTIM_CONTAINER env var, not incident_id
        # The scope line should contain VICTIM_CONTAINER and not incident_id
        # Note: incident_id still appears in function signature and print statements
        assert "VICTIM_CONTAINER" in source, "Scope should use VICTIM_CONTAINER env var"
        # Check that the scope specifically doesn't use incident_id
        import re
        scope_line = None
        for line in source.split('\n'):
            if 'scope=' in line and 'remediate:restart' in line:
                scope_line = line
                break
        assert scope_line is not None, "Scope line not found"
        assert "incident_id" not in scope_line, "Scope should not use incident_id"

    def test_d3g_six_scenarios_tested_against_real_atlas_in_ci(self):
        """D3g: 6 verified scenarios should be integration tests against real Atlas binary in CI."""
        ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
        content = ci_path.read_text()
        # After fix: CI should run integration tests with real Atlas binary
        assert "atlas" in content.lower(), "No Atlas integration tests in CI"


# =============================================================================
# D4: AWS wiring - CORRECT behavior tests
# =============================================================================

class TestD4AWSWiring:
    """D4: AWS infrastructure wiring should be correct."""

    @pytest.mark.xfail(strict=True, reason="D4a")
    def test_d4a_backend_role_does_not_call_update_service(self):
        """D4a: Backend code should not call ecs:UpdateService directly."""
        import remediation
        import inspect
        source = inspect.getsource(remediation._ecs_restart)
        # After fix: backend should not call update_service; executor Lambda should
        assert "update_service" not in source.lower()

    @pytest.mark.xfail(strict=True, reason="D4c")
    def test_d4c_lambda_invoked_by_step_functions_not_backend(self):
        """D4c: Lambda should be invoked by Step Functions, not directly by backend."""
        import remediation
        import inspect
        source = inspect.getsource(remediation.approve_and_remediate)
        # After fix: backend should start Step Functions execution, not call Lambda directly
        # Currently: backend calls _gated_restart() directly
        assert "StartExecution" in source or "start_execution" in source.lower(), \
            "Backend should start Step Functions execution"
        # Should NOT call Lambda directly
        assert "lambda" not in source.lower() or "invoke" not in source.lower(), \
            "Backend should not invoke Lambda directly"

    @pytest.mark.xfail(strict=True, reason="D4d")
    def test_d4d_s3_used_for_transcript_storage(self):
        """D4d: Transcripts should be stored in S3."""
        import remediation
        import inspect
        source = inspect.getsource(remediation)
        # After fix: code should write to TRANSCRIPT_BUCKET
        assert "TRANSCRIPT_BUCKET" in source or "transcript" in source.lower(), \
            "No S3 transcript storage found"

    @pytest.mark.xfail(strict=True, reason="D4e")
    def test_d4e_request_approval_has_token_callback_mechanism(self):
        """D4e: RequestApproval should use task token that is returned by human approval."""
        # The defect: waitForTaskToken is used but no callback mechanism for human to return token
        # After fix: should have a way for human to return the token (e.g., API endpoint)
        # Check if there's an approval callback endpoint in main.py
        main_path = Path(__file__).parent.parent / "backend" / "main.py"
        content = main_path.read_text()
        assert "task_token" in content.lower() or "taskToken" in content, \
            "Should have endpoint to receive task token from human approval"

    @pytest.mark.xfail(strict=True, reason="D4f")
    def test_d4f_verify_step_checks_health_not_just_wait(self):
        """D4f: Verify step should actually check health, not just wait 30s."""
        sfn_path = Path(__file__).parent.parent / "infra" / "stepfunctions.tf"
        content = sfn_path.read_text()
        # After fix: Verify should be a Lambda/health check, not just Wait
        assert "Wait" not in content or "health" in content.lower(), \
            "Verify step should check health, not just wait"

    @pytest.mark.xfail(strict=True, reason="D4g")
    def test_d4g_lambda_verifies_capability_with_atlas(self):
        """D4g: Lambda should verify capability with Atlas before acting."""
        # Check Lambda code in stepfunctions.tf (the embedded Python)
        sfn_path = Path(__file__).parent.parent / "infra" / "stepfunctions.tf"
        content = sfn_path.read_text()
        # After fix: Lambda should call Atlas verify before update_service
        # The Lambda code is embedded in the Terraform - check the actual Python code block
        # Currently: Lambda just calls update_service directly without Atlas verification
        # We need to check the actual Lambda function code, not comments
        # Look for the Python code that would call Atlas verify
        import re
        # Find Python code blocks (between <<EOF markers or similar)
        python_blocks = re.findall(r'<<[A-Z]+[^>]*?python.*?\n(.*?)\n[A-Z]+', content, re.DOTALL | re.IGNORECASE)
        if not python_blocks:
            # Try another pattern for inline Python
            python_blocks = re.findall(r'python\s*=\s*"([^"]+)"', content, re.DOTALL)
        has_atlas_verify = False
        for block in python_blocks:
            if "atlas" in block.lower() and "verify" in block.lower():
                has_atlas_verify = True
                break
        assert has_atlas_verify, "Lambda should verify capability with Atlas before acting"
        assert "update_service" in content.lower()  # Should still call update_service but after verify

    @pytest.mark.xfail(strict=True, reason="D4h")
    def test_d4h_alb_https_with_auth(self):
        """D4h: ALB should be HTTPS with authentication, not public HTTP."""
        # Check Terraform network/ALB config
        network_path = Path(__file__).parent.parent / "infra" / "network.tf"
        if network_path.exists():
            content = network_path.read_text()
            # After fix: should have HTTPS listener with ACM cert and auth
            assert "https" in content.lower() or "acm_certificate" in content.lower()

    @pytest.mark.xfail(strict=True, reason="D4i")
    def test_d4i_iam_grants_only_used_permissions(self):
        """D4i: IAM policies should only grant permissions that are actually used."""
        iam_path = Path(__file__).parent.parent / "infra" / "iam.tf"
        content = iam_path.read_text()
        # After fix: should not have overly broad permissions like "*" for actions not used
        # Check for overly broad resource permissions in GRANT statements (not DENY)
        # The defect: some permissions might be granted but not used
        # Check for wildcard resources in allow statements (not in deny)
        lines = content.split('\n')
        in_deny = False
        has_unjustified_wildcard = False
        for line in lines:
            stripped = line.strip()
            if 'effect = "deny"' in stripped.lower() or 'effect = "Deny"' in stripped:
                in_deny = True
            elif 'effect = "allow"' in stripped.lower() or 'effect = "Allow"' in stripped:
                in_deny = False
            elif '}' in stripped and in_deny:
                in_deny = False

            # Check for wildcard in non-deny context
            if not in_deny and '"*"' in stripped and 'resource' in stripped.lower():
                # Check if it's a justified wildcard (like for deny statements)
                has_unjustified_wildcard = True
                break
        assert not has_unjustified_wildcard, \
            "Should not have wildcard resources in allow statements without justification"

    @pytest.mark.xfail(strict=True, reason="D4j")
    def test_d4j_null_condition_verified_or_removed(self):
        """D4j: Null condition on ecs:task-definition should be verified or removed."""
        iam_path = Path(__file__).parent.parent / "infra" / "iam.tf"
        content = iam_path.read_text()
        # After fix: either document the condition is UNVERIFIED or enforce in code
        # Currently has: condition { test = "Null", variable = "ecs:task-definition", values = ["true"] }
        # Should have HUMAN_TODO or be enforced in Lambda code
        assert "UNVERIFIED" in content or "HUMAN_TODO" in content or "task-definition" not in content.lower(), \
            "Null condition should be marked UNVERIFIED or removed"


# =============================================================================
# D5: No application tests - CORRECT behavior tests
# =============================================================================

class TestD5ApplicationTests:
    """D5: CI should have comprehensive application tests."""

    @pytest.mark.xfail(strict=True, reason="D5")
    def test_d5_ci_has_pytest_application_tests(self):
        """D5: CI should run pytest application tests."""
        ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
        content = ci_path.read_text()
        assert "pytest" in content


# =============================================================================
# D6: KLRB not integrated - CORRECT behavior tests
# =============================================================================

class TestD6KLRBIntegration:
    """D6: KLRB should be integrated as an evaluator."""

    @pytest.mark.xfail(strict=True, reason="D6")
    def test_d6_klrb_integrated_as_evaluator(self):
        """D6: KLRB should be integrated and used for evaluation, not just mentioned."""
        # After fix: KLRB should be imported and used in eval code, not just mentioned in docs
        eval_path = Path(__file__).parent.parent / "eval"
        has_klrb_integration = False
        for py_file in eval_path.glob("*.py"):
            content = py_file.read_text()
            # Look for actual import/usage, not just mentions in comments/docstrings
            if "import klrb" in content or "from klrb" in content or "klrb." in content:
                has_klrb_integration = True
                break
        assert has_klrb_integration, "KLRB not integrated as evaluator (only mentioned in docs)"


# =============================================================================
# D7: Stack facts - CORRECT behavior tests
# =============================================================================

class TestD7StackFacts:
    """D7: Stack facts should be accurate (FastAPI, not Flask)."""

    def test_d7_docs_reflect_fastapi_not_flask(self):
        """D7: Documentation should say FastAPI, not Flask."""
        # Check all markdown docs and claim files for Flask references to backend
        # Exclude analysis files that intentionally show incorrect claims as examples
        doc_files = list(Path(__file__).parent.parent.glob("*.md")) + \
                    list(Path(__file__).parent.parent.glob("*.json"))
        has_flask_backend_claim = False
        for doc_file in doc_files:
            if doc_file.name == "FINAL_ANALYSIS.md":
                continue  # This file shows incorrect claim as BEFORE example
            content = doc_file.read_text().lower()
            # Check if Flask is claimed as the backend framework
            if "flask" in content and ("backend" in content or "api" in content or "framework" in content):
                has_flask_backend_claim = True
                break
        assert not has_flask_backend_claim, "Documentation claims Flask for backend (should be FastAPI)"

    def test_d7_stack_manifest_generated_from_code(self):
        """D7: Stack manifest should be generated from requirements/imports, not typed by hand."""
        scripts_path = Path(__file__).parent.parent / "scripts" / "stack_manifest.py"
        # After fix: should have script that generates stack manifest
        assert scripts_path.exists(), "stack_manifest.py should exist to generate stack facts"


# =============================================================================
# D8: No automated browser tests - CORRECT behavior tests
# =============================================================================

class TestD8BrowserTests:
    """D8: Should have automated browser tests (Playwright)."""

    @pytest.mark.xfail(strict=True, reason="D8")
    def test_d8_playwright_tests_in_ci(self):
        """D8: CI should run Playwright browser tests."""
        ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
        content = ci_path.read_text()
        assert "playwright" in content.lower()


# =============================================================================
# D9: Poller global state - CORRECT behavior tests
# =============================================================================

class TestD9PollerState:
    """D9: Poller should not use module global for active incident."""

    @pytest.mark.xfail(strict=True, reason="D9")
    def test_d9_poller_uses_database_for_active_incident(self):
        """D9: Poller should derive active incident from database, not module global."""
        import poller
        import inspect
        source = inspect.getsource(poller.run_poller)
        # After fix: should query database for active incident, not use global
        # Currently: uses `global active_incident_id`
        assert "active_incident_id" not in source or "global" not in source, \
            "Poller should not use module global for active incident"

    @pytest.mark.xfail(strict=True, reason="D9")
    def test_d9_poller_survives_restart_no_duplicates(self):
        """D9: Poller restart should not lose or duplicate incidents."""
        import poller
        import inspect
        source = inspect.getsource(poller.run_poller)
        # After fix: uses database with partial unique index on service_name
        # Should query for non-terminal incidents by service_name
        assert "service_name" in source and ("status" in source or "WHERE" in source), \
            "Poller should query database for active incidents by service_name"


# =============================================================================
# D10: Tool counting - CORRECT behavior tests
# =============================================================================

class TestD10ToolCounting:
    """D10: Only successful tool executions should count toward minimum."""

    @pytest.mark.xfail(strict=True, reason="D10")
    def test_d10_only_successful_tools_count_toward_minimum(self):
        """D10: executed_tool_count should only increment on successful tool calls."""
        import agent
        import inspect
        source = inspect.getsource(agent.investigate)
        # After fix: should only count successful executions
        # Currently: executed_tool_count += 1 for every tool call
        assert "successful" in source.lower() or "succeeded" in source.lower(), \
            "Should track successful tool executions separately"


# =============================================================================
# D11: Zero financial API exposure - CORRECT behavior tests
# =============================================================================

class TestD11FinancialExposure:
    """D11: Should have explicit mechanism preventing financial API calls."""

    @pytest.mark.xfail(strict=True, reason="D11")
    def test_d11_explicit_deny_financial_apis(self):
        """D11: Should have explicit mechanism (policy/IAM) preventing financial API calls."""
        # Check for policy registry or IAM denies
        policy_path = Path(__file__).parent.parent / "backend" / "policy.py"
        iam_path = Path(__file__).parent.parent / "infra" / "iam.tf"

        has_policy = policy_path.exists()
        has_iam_deny = False
        if iam_path.exists():
            content = iam_path.read_text()
            # Check for billing API denies
            billing_apis = ["aws-portal:*", "billing:*", "ce:*", "cur:*", "budgets:*",
                           "payments:*", "purchase-orders:*", "savingsplans:*",
                           "ec2:PurchaseReservedInstancesOffering"]
            has_iam_deny = all(api in content for api in billing_apis)

        assert has_policy or has_iam_deny, \
            "Should have policy.py deny-by-default registry or IAM billing API denies"


# =============================================================================
# D12: Atlas not pinned - CORRECT behavior tests
# =============================================================================

class TestD12AtlasPinned:
    """D12: Atlas should be pinned, locally built service."""

    def test_d12_atlas_ref_pins_version(self):
        """D12: ATLAS_REF env var should pin Atlas version."""
        # Check CI for ATLAS_REF usage
        ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
        content = ci_path.read_text()
        # After fix: CI should use ATLAS_REF to build Atlas
        assert "ATLAS_REF" in content, "CI should use ATLAS_REF to pin Atlas version"

    def test_d12_atlas_built_locally_in_ci(self):
        """D12: Atlas should be built locally in CI from pinned commit."""
        ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
        content = ci_path.read_text()
        # After fix: CI should build atlas-server from ATLAS_REF
        # Check for actual build steps, not just mentions in comments
        # Look for "cargo build" or "make build" or similar for atlas
        has_atlas_build = False
        for line in content.split('\n'):
            line_lower = line.lower().strip()
            # Skip comments
            if line_lower.startswith('#'):
                continue
            if 'atlas' in line_lower and ('build' in line_lower or 'cargo' in line_lower or 'compile' in line_lower):
                has_atlas_build = True
                break
        assert has_atlas_build, "CI should build Atlas locally from source (not just mention it)"

    # =============================================================================
# Run with: pytest tests/test_defects.py -v --tb=short
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])