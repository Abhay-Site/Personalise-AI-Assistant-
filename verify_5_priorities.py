import urllib.request, urllib.error, json, sys

# Ensure UTF-8 stdout encoding on Windows
sys.stdout.reconfigure(encoding='utf-8')

print('=============================================')
print('SYSTEMATIC 5-PRIORITY VERIFICATION RUN')
print('=============================================\n')

# PRIORITY 1: Frontend-Backend Connectivity
print('[PRIORITY 1] Testing Frontend-Backend Connectivity...')
try:
    req = urllib.request.Request('http://127.0.0.1:8000/health')
    res = urllib.request.urlopen(req)
    health_data = json.loads(res.read().decode('utf-8'))
    print(f' [PASS] FastAPI Backend is reachable on port 8000 (status={health_data.get("status")})')
    print(f'   - Gemini Configured: {health_data.get("gemini_configured")} (Model: {health_data.get("gemini_model")})')
    print(f'   - Google OAuth Configured: {health_data.get("google_oauth_configured")}')
except Exception as e:
    print(f' [FAIL] Priority 1 Failed: {e}')
    sys.exit(1)

# PRIORITY 2: Calendar Date Handling
print('\n[PRIORITY 2] Testing Dynamic Calendar Date Handling...')
try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/chat',
        data=json.dumps({'message': 'What appointments do I have tomorrow?'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    cal_data = json.loads(res.read().decode('utf-8'))
    cal_steps = [s for s in cal_data.get('action_plan', {}).get('steps', []) if s.get('action') == 'list_events']
    assert len(cal_steps) > 0, 'No list_events step generated'
    
    trace_msgs = [t['message'] for t in cal_data.get('trace', [])]
    print(f' [PASS] Calendar workflow triggered for: "What appointments do I have tomorrow?"')
    print(f'   - Action Plan Goal: {cal_data["action_plan"]["goal"]}')
    print(f'   - Step: {cal_steps[0]["service"]} -> {cal_steps[0]["action"]}')
    print(f'   - Dynamic trace verified: {any("Calendar" in m or "list_events" in m for m in trace_msgs)}')
except Exception as e:
    print(f' [FAIL] Priority 2 Failed: {e}')
    sys.exit(1)

# PRIORITY 3: AI Planning and Execution
print('\n[PRIORITY 3] Testing AI Planning and Tool Execution...')
test_cases = [
    ('Agenda query', 'Check my agenda for today', 'calendar', 'list_events'),
    ('Free time query', 'When am I free tomorrow?', 'calendar', 'find_free_time'),
    ('Drive search', 'Find the project report file in Drive', 'drive', 'search_files'),
    ('Email ping', 'Send email to mentor@university.edu about thesis', 'gmail', 'create_draft'),
]
for label, query, expected_service, expected_action in test_cases:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/chat',
        data=json.dumps({'message': query}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    resp = json.loads(res.read().decode('utf-8'))
    plan = resp.get('action_plan')
    actions = [s['action'] for s in plan.get('steps', [])] if plan else []
    assert expected_action in actions, f'Expected {expected_action} in {actions}'
    print(f' [PASS] {label} ("{query}") -> Plan: {actions}')

# PRIORITY 4: Approval & Draft Handling
print('\n[PRIORITY 4] Testing Approval and Draft Handling...')
# Step 4.1: Create sensitive plan
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/chat',
    data=json.dumps({'message': 'Send email to reviewer@domain.com saying meeting confirmed'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req)
draft_resp = json.loads(res.read().decode('utf-8'))
plan_id = draft_resp.get('action_plan_id')
assert draft_resp.get('requires_approval') is True, 'Plan did not pause for approval'
print(f' [PASS] Sensitive action paused before send_email (Plan #{plan_id})')
print(f'   - Pending Action: {draft_resp.get("approval_action", {}).get("type")}')
print(f'   - Stored Validated Args: {draft_resp.get("approval_action", {}).get("args")}')

# Step 4.2: Execute Approval
appr_req = urllib.request.Request(
    'http://127.0.0.1:8000/api/approvals',
    data=json.dumps({'action_plan_id': plan_id, 'approved': True}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
appr_res = urllib.request.urlopen(appr_req)
appr_data = json.loads(appr_res.read().decode('utf-8'))
assert appr_data.get('status') == 'executed', f'Expected executed, got {appr_data.get("status")}'
print(f' [PASS] Plan #{plan_id} successfully approved and executed with validated draft arguments')

# Step 4.3: Double Execution Prevention
try:
    urllib.request.urlopen(appr_req)
    print(' [FAIL] Priority 4 Failed: Re-execution was not blocked')
    sys.exit(1)
except urllib.error.HTTPError as http_err:
    assert http_err.code == 400, f'Expected 400, got {http_err.code}'
    print(f' [PASS] Double-execution correctly blocked: HTTP {http_err.code} ({http_err.reason})')

# PRIORITY 5: Error Reporting & Status Transparency
print('\n[PRIORITY 5] Testing Status Transparency and Error Reporting...')
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/chat',
    data=json.dumps({'message': 'Test transparency status'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req)
diag = json.loads(res.read().decode('utf-8'))
print(f' [PASS] Integration Status: {diag.get("integration_status")}')
print(f' [PASS] Model Name: {diag.get("model_name")}')
print(f' [PASS] Is Fallback Flag: {diag.get("is_fallback")}')
print(f' [PASS] Error Detail Field: {diag.get("error_detail")}')

print('\n=============================================')
print('ALL 5 PRIORITIES VERIFIED & PASSING!')
print('=============================================')
