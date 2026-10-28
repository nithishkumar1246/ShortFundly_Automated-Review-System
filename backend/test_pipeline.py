import urllib.request
import json
import io

def post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req).read().decode())

def get(url):
    return json.loads(urllib.request.urlopen(url).read().decode())

def post_multipart(url, fields, files):
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = bytearray()
    
    for k, v in fields.items():
        body.extend(f'--{boundary}\r\n'.encode())
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        body.extend(f'{v}\r\n'.encode())
        
    for k, (filename, content, content_type) in files.items():
        body.extend(f'--{boundary}\r\n'.encode())
        body.extend(f'Content-Disposition: form-data; name="{k}"; filename="{filename}"\r\n'.encode())
        body.extend(f'Content-Type: {content_type}\r\n\r\n'.encode())
        body.extend(content)
        body.extend(b'\r\n')
        
    body.extend(f'--{boundary}--\r\n'.encode())
    
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}'
    })
    return json.loads(urllib.request.urlopen(req).read().decode())

def run_tests():
    # Reset intern to Stage 1 to ensure a clean pipeline test run
    post('http://127.0.0.1:8000/api/interns/INT-101/reset', {})

    print("=====================================================")
    print("STEP 1: Verify Intern & Retrieve DOJ & Schedule")
    print("=====================================================")
    v = post('http://127.0.0.1:8000/api/interns/verify', {'query': 'Aarav Sharma'})
    print("Intern Name:", v['intern']['name'])
    print("Intern ID:", v['intern']['intern_id'])
    print("Verified DOJ:", v['intern']['doj'])
    print("Assigned Master Task:", v['assigned_task']['title'])
    print(f"Scheduled Stages ({len(v['review_schedule'])} total):")
    for s in v['review_schedule']:
        print(f"  Stage {s['stage_number']}: {s['scheduled_date']} (Gap: {s['gap_days']} days) | Meet: {s['meeting_link']}")

    print("\n=====================================================")
    print("STEP 2: Dispatch / Verify Stage 1 Invitation Email")
    print("=====================================================")
    inv = post('http://127.0.0.1:8000/api/interns/INT-101/send-invitation', {})
    print("Invitation Status:", inv['message'])
    print("Invited Meet Link:", inv['dispatch']['meeting_link'])

    print("\n=====================================================")
    print("STEP 3: Submit GitHub Repo for Review Stage 1")
    print("=====================================================")
    sub1 = post('http://127.0.0.1:8000/api/reviews/submit', {
        'intern_id': 'INT-101',
        'github_url': 'https://github.com/aarav-sharma/cloud-microservices-ai'
    })
    print("Evaluation Score:", sub1['evaluation']['score'], sub1['evaluation']['verdict'])
    print("Completed Modules Verified:", len(sub1['evaluation']['completed_modules']))
    print("Necessary Code Corrections:", len(sub1['evaluation']['code_corrections']))
    print("Missing Components:", len(sub1['evaluation']['missing_components']))
    print("Modules to Add for Next Stage:", len(sub1['evaluation']['modules_to_add']))
    print("Email Dispatched To:", sub1['email_dispatch']['recipient_email'])
    print("Next Review Scheduled:", sub1['next_review']['scheduled_date'], "| Meet Link:", sub1['next_review']['meeting_link'])

    print("\n=====================================================")
    print("STEP 4: Test Document / Code Archive Upload for Stage 2")
    print("=====================================================")
    sample_code = b"# Python FastAPI Backend\nimport fastapi\n# Implemented CRUD endpoints\n"
    sub2 = post_multipart('http://127.0.0.1:8000/api/reviews/upload', 
        fields={'intern_id': 'INT-101'},
        files={'file': ('retail_shelf_code_stage2.zip', sample_code, 'application/zip')}
    )
    print("Document Upload Result:", sub2['evaluation']['submission_type'], sub2['evaluation']['item_label'])
    print("Score:", sub2['evaluation']['score'], "| Verdict:", sub2['evaluation']['verdict'])
    print("Next Stage Assigned:", sub2['next_review']['stage_name'])

    print("\n=====================================================")
    print("STEP 5: Progress Remaining Stages 3 -> 4 to Completion")
    print("=====================================================")
    for stage_num in [3, 4]:
        sub = post('http://127.0.0.1:8000/api/reviews/submit', {
            'intern_id': 'INT-101',
            'github_url': 'https://github.com/aarav-sharma/cloud-microservices-ai'
        })
        print(f"Stage {stage_num} Finished. Score: {sub['evaluation']['score']} | Intern Status: {sub['intern']['status']} | Final Stage: {sub['is_final_stage']}")

    print("\n=====================================================")
    print("STEP 6: Verify Email Dispatch Logs (Both Invites & Evaluations)")
    print("=====================================================")
    emails = get('http://127.0.0.1:8000/api/emails?intern_id=INT-101')
    print("Total Dispatched Emails in DB:", len(emails['emails']))
    for em in emails['emails']:
        print(f"  ID {em['id']} | Type: {em.get('email_type', 'EVALUATION')} | Stage {em['stage_number']} | Subject: {em['subject'][:45]}... | To: {em['recipient_email']}")

    print("\n=====================================================")
    print("STEP 7: Reset Intern back to Stage 1 for live demo")
    print("=====================================================")
    reset_res = post('http://127.0.0.1:8000/api/interns/INT-101/reset', {})
    print("Reset Message:", reset_res['message'])
    print("Intern Stage is now:", reset_res['intern']['current_review_stage'])

if __name__ == '__main__':
    run_tests()
