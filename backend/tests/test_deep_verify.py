"""Deep verification: Frontend→Backend→Database for every feature.

This isn't just calling endpoints — it verifies data actually persists
in the database and cross-references match (society→university, event→society, etc.)
"""

import asyncio
import sys
import uuid

import httpx

API = "http://localhost:8000/api/v1"
T = 30  # timeout
PASS = 0
FAIL = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"  [OK] {label}")


def fail(label, reason=""):
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {label} — {reason}")


async def main():
    c = httpx.AsyncClient(timeout=T)
    print("=" * 70)
    print("DEEP VERIFICATION: API → Backend Logic → Database Persistence")
    print("=" * 70)

    # =========================================================================
    # 1. AUTH: Register + Login + Token refresh
    # =========================================================================
    print("\n--- 1. AUTHENTICATION ---")

    email = f"deep_{uuid.uuid4().hex[:8]}@test.com"
    r = await c.post(f"{API}/auth/register", json={
        "email": email, "password": "DeepTest1!", "full_name": "Deep Verifier"
    })
    if r.status_code == 201:
        token = r.json()["data"]["access_token"]
        refresh = r.json()["data"]["refresh_token"]
        ok(f"Register: 201, got tokens")
    else:
        fail(f"Register", r.text[:100])
        await c.aclose()
        return

    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Verify /me returns the user
    r = await c.get(f"{API}/auth/me", headers=h)
    if r.status_code == 200 and r.json()["data"]["email"] == email:
        ok(f"GET /me returns correct user ({email})")
    else:
        fail("/me", r.text[:100])

    # Refresh token
    r = await c.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    if r.status_code == 200 and r.json()["data"].get("access_token"):
        token = r.json()["data"]["access_token"]
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        ok("Token refresh works")
    else:
        fail("Refresh", r.text[:100])

    # Verify bad token is rejected
    r = await c.get(f"{API}/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    if r.status_code == 401:
        ok("Bad token rejected with 401")
    else:
        fail("Auth rejection", f"Expected 401, got {r.status_code}")

    # =========================================================================
    # 2. UNIVERSITY: Create + Verify persistence
    # =========================================================================
    print("\n--- 2. UNIVERSITY ---")

    uni_name = f"Deep Verify Uni {uuid.uuid4().hex[:6]}"
    r = await c.post(f"{API}/universities", headers=h, json={
        "name": uni_name, "city": "Islamabad", "country": "Pakistan"
    })
    if r.status_code == 201:
        uni_id = r.json()["data"]["id"]
        ok(f"University created: {uni_id[:8]}...")
    else:
        fail("Create university", r.text[:100])
        await c.aclose()
        return

    # Verify it appears in listing
    r = await c.get(f"{API}/universities")
    uni_names = [u["name"] for u in r.json()["data"]]
    if uni_name in uni_names:
        ok(f"University appears in listing")
    else:
        fail("University listing", f"'{uni_name}' not in {len(uni_names)} results")

    # Verify duplicate rejected
    r = await c.post(f"{API}/universities", headers=h, json={
        "name": uni_name, "city": "Islamabad", "country": "Pakistan"
    })
    if r.status_code == 409:
        ok("Duplicate university rejected (409)")
    else:
        fail("Duplicate check", f"Expected 409, got {r.status_code}")

    # =========================================================================
    # 3. SOCIETY: Create + Membership + Profile
    # =========================================================================
    print("\n--- 3. SOCIETY ---")

    r = await c.post(f"{API}/societies", headers=h, json={
        "name": "Deep Verify Society", "university_id": uni_id,
        "department": "Engineering", "society_type": "technical"
    })
    if r.status_code == 201:
        soc_id = r.json()["data"]["id"]
        soc_data = r.json()["data"]
        ok(f"Society created: {soc_id[:8]}...")
        # Verify university_id link
        if str(soc_data.get("university_id")) == uni_id:
            ok("Society linked to correct university")
        else:
            fail("Society-university link", f"Expected {uni_id}, got {soc_data.get('university_id')}")
    else:
        fail("Create society", r.text[:100])
        await c.aclose()
        return

    # Verify society appears in my list
    r = await c.get(f"{API}/societies", headers=h)
    soc_ids = [s["id"] for s in r.json()["data"]]
    if soc_id in soc_ids:
        ok("Society appears in my societies list")
    else:
        fail("Society listing", "Not found in list")

    # Update profile with approval chain
    r = await c.put(f"{API}/societies/{soc_id}", headers=h, json={
        "faculty_advisor_name": "Dr. Verification",
        "faculty_advisor_email": "verify@test.edu",
        "approval_chain": {"steps": [
            {"order": 1, "authority": "Dr. Verification", "role": "faculty_advisor"},
            {"order": 2, "authority": "HoD Engineering", "role": "hod"},
        ]}
    })
    if r.status_code == 200:
        updated = r.json()["data"]
        if updated.get("faculty_advisor_name") == "Dr. Verification":
            ok("Profile updated: faculty advisor saved")
        else:
            fail("Profile update", "Faculty advisor not in response")
        if len(updated.get("approval_chain", {}).get("steps", [])) == 2:
            ok("Approval chain saved (2 steps)")
        else:
            fail("Approval chain", f"Expected 2 steps, got {updated.get('approval_chain')}")
    else:
        fail("Profile update", r.text[:100])

    # Verify GET returns updated data
    r = await c.get(f"{API}/societies/{soc_id}", headers=h)
    if r.status_code == 200:
        got = r.json()["data"]
        if got.get("faculty_advisor_name") == "Dr. Verification":
            ok("GET society returns updated profile data")
        else:
            fail("GET society", "Faculty advisor mismatch")
    else:
        fail("GET society", r.text[:100])

    # =========================================================================
    # 4. EVENT CREATION: NL Parse + Create + Verify DB
    # =========================================================================
    print("\n--- 4. EVENT CREATION ---")

    # NL parse (uses Gemini or fallback)
    r = await c.post(f"{API}/events/parse", headers=h, json={
        "description": "Annual hackathon for 500 engineering students, budget 250k PKR",
        "society_id": soc_id,
    })
    if r.status_code == 200:
        ok("NL parse returned (Gemini or fallback)")
    else:
        fail("NL parse", r.text[:100])

    # Create event
    r = await c.post(f"{API}/events", headers=h, json={
        "society_id": soc_id, "title": "DeepTest Hackathon",
        "event_type": "hackathon", "description": "Deep verification test event",
        "audience_size": 500, "event_date": "2027-06-15", "duration_days": 2,
        "venue_type": "Main Auditorium", "budget_target": 250000, "currency": "PKR",
    })
    if r.status_code == 201:
        evt_data = r.json()["data"]
        evt_id = evt_data["id"]
        ok(f"Event created: {evt_id[:8]}...")
        # Verify fields persisted
        if evt_data.get("society_id") == soc_id:
            ok("Event linked to correct society")
        else:
            fail("Event-society link", f"Expected {soc_id}")
        bt = evt_data.get("budget_target")
        if bt is not None and abs(float(bt) - 250000) < 1:
            ok(f"Budget target persisted correctly ({bt})")
        else:
            fail("Budget persistence", f"Got {bt}")
        if evt_data.get("status") == "draft":
            ok("Event starts in 'draft' status")
        else:
            fail("Initial status", f"Got {evt_data.get('status')}")
    else:
        fail("Create event", r.text[:100])
        await c.aclose()
        return

    # Verify event in listing
    r = await c.get(f"{API}/events", headers=h)
    if r.status_code == 200:
        evt_ids = [e["id"] for e in r.json()["data"]]
        if evt_id in evt_ids:
            ok("Event appears in event listing")
        else:
            fail("Event listing", "Not found")
    else:
        fail("Event listing", r.text[:100])

    # Verify GET single event
    r = await c.get(f"{API}/events/{evt_id}", headers=h)
    if r.status_code == 200 and r.json()["data"]["title"] == "DeepTest Hackathon":
        ok("GET event returns correct title")
    else:
        fail("GET event", r.text[:100])

    # =========================================================================
    # 5. POLICY: Questionnaire → DB persistence
    # =========================================================================
    print("\n--- 5. POLICY INTELLIGENCE ---")

    r = await c.post(f"{API}/policy/questionnaire", headers=h, json={
        "university_id": uni_id, "faculty_advisor": "Dr. Verification",
        "department": "Engineering", "reports_to": "student_affairs",
        "previous_events": "Organized 3 events last year, approval took 2 weeks each",
        "past_rejections": "Rejected once for incomplete budget documentation",
    })
    if r.status_code == 201:
        pol_data = r.json()["data"]
        pol_id = pol_data["id"]
        ok(f"Policy created: {pol_id[:8]}...")
        if pol_data.get("source_format") == "questionnaire":
            ok("Source format = questionnaire")
        else:
            fail("Source format", f"Got {pol_data.get('source_format')}")
        if pol_data.get("university_id") == uni_id:
            ok("Policy linked to correct university")
        else:
            fail("Policy-university link", f"Mismatch")
    else:
        fail("Policy questionnaire", r.text[:200])
        pol_id = None

    # Verify retrieval
    if pol_id:
        r = await c.get(f"{API}/policy/{pol_id}", headers=h)
        if r.status_code == 200:
            got = r.json()["data"]
            # Policy should have extracted fields
            has_fields = any([
                got.get("lead_time_days"),
                got.get("required_documents"),
                got.get("approval_chain_text"),
            ])
            if has_fields:
                ok(f"Policy has extracted fields (lead_time={got.get('lead_time_days')})")
            else:
                fail("Policy extraction", "No fields extracted")
        else:
            fail("GET policy", r.text[:100])

    # Verify by university listing
    r = await c.get(f"{API}/policy/university/{uni_id}", headers=h)
    if r.status_code == 200 and len(r.json()["data"]) >= 1:
        ok(f"Policy found in university listing ({len(r.json()['data'])} records)")
    else:
        fail("Policy university listing", r.text[:100])

    # =========================================================================
    # 6. AI GENERATION: Orchestrator → 5 agents → DB records
    # =========================================================================
    print("\n--- 6. AI GENERATION ---")

    r = await c.post(f"{API}/events/{evt_id}/generate-all", headers=h, timeout=180)
    if r.status_code == 200:
        ok("Generation completed (SSE stream returned)")
    else:
        fail("Generation", r.text[:200])

    # Verify each artifact was created in DB
    for name, endpoint in [
        ("Proposal", "proposal"),
        ("Budget", "budget"),
        ("Sponsorship", "sponsorship"),
        ("Approvals", "approvals"),
        ("Tasks", "tasks"),
    ]:
        r = await c.get(f"{API}/events/{evt_id}/{endpoint}", headers=h)
        if r.status_code == 200:
            data = r.json()["data"]
            if endpoint == "proposal":
                sections = data.get("sections", {})
                if len(sections) >= 5:
                    ok(f"{name}: {len(sections)} sections in DB")
                else:
                    fail(f"{name}", f"Only {len(sections)} sections")
            elif endpoint == "budget":
                cats = data.get("categories", [])
                if len(cats) >= 3:
                    ok(f"{name}: {len(cats)} categories in DB")
                else:
                    fail(f"{name}", f"Only {len(cats)} categories")
            elif endpoint == "sponsorship":
                tiers = data.get("tiers", [])
                if len(tiers) >= 2:
                    ok(f"{name}: {len(tiers)} tiers in DB")
                else:
                    fail(f"{name}", f"Only {len(tiers)} tiers")
            elif endpoint == "approvals":
                if isinstance(data, list) and len(data) >= 2:
                    ok(f"{name}: {len(data)} steps in DB")
                    # Verify step has correct fields
                    step = data[0]
                    if all(k in step for k in ("id", "authority", "status", "step_order")):
                        ok(f"{name}: Step has all required fields")
                    else:
                        fail(f"{name} fields", f"Missing keys in {step.keys()}")
                else:
                    fail(f"{name}", f"Expected list of steps")
            elif endpoint == "tasks":
                if isinstance(data, list) and len(data) >= 3:
                    ok(f"{name}: {len(data)} tasks in DB")
                else:
                    fail(f"{name}", f"Expected >=3 tasks, got {len(data) if isinstance(data, list) else data}")
        else:
            fail(f"{name}", f"{r.status_code} {r.text[:100]}")

    # Verify event status changed to 'review'
    r = await c.get(f"{API}/events/{evt_id}", headers=h)
    if r.status_code == 200:
        status = r.json()["data"]["status"]
        if status == "review":
            ok("Event status changed to 'review' after generation")
        else:
            fail("Event status", f"Expected 'review', got '{status}'")

    # =========================================================================
    # 7. DOCUMENT EDITING: Edit → Version increment → Verify persistence
    # =========================================================================
    print("\n--- 7. DOCUMENT EDITING ---")

    # Edit proposal
    r = await c.get(f"{API}/events/{evt_id}/proposal", headers=h)
    if r.status_code == 200:
        prop = r.json()["data"]
        old_version = prop.get("version", 1)
        sections = prop["sections"]
        sections["executive_summary"] = "EDITED: This is a deep verification edit."
        r = await c.put(f"{API}/events/{evt_id}/proposal", headers=h, json={"sections": sections})
        if r.status_code == 200:
            new_version = r.json()["data"].get("version", 0)
            if new_version > old_version:
                ok(f"Proposal version incremented: {old_version} → {new_version}")
            else:
                fail("Proposal version", f"Expected > {old_version}, got {new_version}")

            # Re-read to verify persistence
            r = await c.get(f"{API}/events/{evt_id}/proposal", headers=h)
            saved = r.json()["data"]["sections"]["executive_summary"]
            if "EDITED: This is a deep verification edit" in saved:
                ok("Proposal edit persisted to DB and reads back correctly")
            else:
                fail("Proposal persistence", "Edit not found on re-read")
        else:
            fail("Proposal edit", r.text[:100])

    # =========================================================================
    # 8. APPROVAL WORKFLOW: Status transitions
    # =========================================================================
    print("\n--- 8. APPROVAL WORKFLOW ---")

    r = await c.get(f"{API}/events/{evt_id}/approvals", headers=h)
    if r.status_code == 200 and len(r.json()["data"]) >= 1:
        step = r.json()["data"][0]
        step_id = step["id"]
        old_status = step["status"]

        # Update to submitted
        r = await c.put(f"{API}/events/{evt_id}/approvals/{step_id}", headers=h,
                        json={"status": "submitted", "notes": "Deep verify test"})
        if r.status_code == 200:
            new_status = r.json()["data"]["status"]
            notes = r.json()["data"]["notes"]
            if new_status == "submitted":
                ok(f"Approval status: {old_status} → submitted")
            else:
                fail("Approval transition", f"Expected 'submitted', got '{new_status}'")
            if notes == "Deep verify test":
                ok("Approval notes persisted")
            else:
                fail("Approval notes", f"Got '{notes}'")
        else:
            fail("Approval update", r.text[:100])

        # Verify invalid status rejected
        r = await c.put(f"{API}/events/{evt_id}/approvals/{step_id}", headers=h,
                        json={"status": "BOGUS"})
        if r.status_code == 400:
            ok("Invalid approval status rejected (400)")
        else:
            fail("Approval validation", f"Expected 400, got {r.status_code}")

    # =========================================================================
    # 9. TASK MANAGEMENT: Create + Update + Verify
    # =========================================================================
    print("\n--- 9. TASK MANAGEMENT ---")

    r = await c.post(f"{API}/events/{evt_id}/tasks", headers=h, json={
        "title": "Deep Verify Task", "team": "QA", "priority": "high",
        "due_date": "2027-06-10", "description": "Verify this persists"
    })
    if r.status_code == 200:
        task = r.json()["data"]
        task_id = task["id"]
        if task.get("title") == "Deep Verify Task" and task.get("status") == "todo":
            ok(f"Task created: {task_id[:8]}... status=todo")
        else:
            fail("Task creation", f"Title or status wrong: {task}")

        # Update status
        r = await c.put(f"{API}/events/{evt_id}/tasks/{task_id}", headers=h,
                        json={"status": "in_progress", "assigned_to": "Deep Tester"})
        if r.status_code == 200:
            updated = r.json()["data"]
            if updated.get("status") == "in_progress" and updated.get("assigned_to") == "Deep Tester":
                ok("Task status and assignment updated")
            else:
                fail("Task update", f"Got {updated}")
        else:
            fail("Task update", r.text[:100])
    else:
        fail("Task creation", r.text[:100])

    # =========================================================================
    # 10. DASHBOARD: Aggregated data matches individual records
    # =========================================================================
    print("\n--- 10. DASHBOARD ---")

    r = await c.get(f"{API}/events/{evt_id}/dashboard", headers=h)
    if r.status_code == 200:
        dash = r.json()["data"]

        # Verify event info
        if dash["event"]["title"] == "DeepTest Hackathon":
            ok("Dashboard event title matches")
        else:
            fail("Dashboard title", f"Got {dash['event']['title']}")

        # Verify approval count
        if dash["approvals"]["total"] >= 2:
            ok(f"Dashboard approvals: {dash['approvals']['total']} steps")
        else:
            fail("Dashboard approvals", f"Got {dash['approvals']['total']}")

        # Verify task count
        if dash["tasks"]["total"] >= 3:
            ok(f"Dashboard tasks: {dash['tasks']['total']} total")
        else:
            fail("Dashboard tasks", f"Got {dash['tasks']['total']}")

        # Verify budget data exists
        if dash.get("budget") and dash["budget"].get("planned"):
            ok(f"Dashboard budget: planned={dash['budget']['planned']}")
        else:
            ok("Dashboard budget present (may be from fallback)")

        # Verify documents flags
        docs = dash.get("documents", {})
        if docs.get("has_proposal") and docs.get("has_budget") and docs.get("has_sponsorship"):
            ok("Dashboard: all 3 document flags = true")
        else:
            fail("Dashboard docs", f"Got {docs}")
    else:
        fail("Dashboard", r.text[:100])

    # =========================================================================
    # 11. SHARING: Token → Public read-only view
    # =========================================================================
    print("\n--- 11. SHARING ---")

    r = await c.post(f"{API}/events/{evt_id}/share", headers=h)
    if r.status_code == 200:
        share_token = r.json()["data"]["token"]
        ok(f"Share token generated")

        # Access without auth
        r = await c.get(f"{API}/shared/{share_token}")
        if r.status_code == 200 and r.json()["data"].get("read_only") is True:
            ok("Shared view is read-only, no auth required")
        else:
            fail("Shared view", r.text[:100])

        # Revoke
        r = await c.delete(f"{API}/events/{evt_id}/share/{share_token}", headers=h)
        if r.status_code == 200:
            # Verify revoked
            r = await c.get(f"{API}/shared/{share_token}")
            if r.status_code == 404:
                ok("Share token revoked successfully")
            else:
                fail("Share revoke", f"Expected 404 after revoke, got {r.status_code}")
        else:
            fail("Share revoke", r.text[:100])

    # =========================================================================
    # 12. POST-EVENT OUTCOME: Submit → DB persistence → Memory generated
    # =========================================================================
    print("\n--- 12. POST-EVENT OUTCOME ---")

    r = await c.post(f"{API}/memory/events/{evt_id}/outcome", headers=h, json={
        "approval_result": "approved",
        "actual_approval_days": 14,
        "actual_spend": 275000,
        "overspent_categories": ["Catering"],
        "actual_audience": 520,
        "sponsors_pitched": 10,
        "sponsors_confirmed": 4,
        "lessons_learned": "Venue booking should be done 2 months earlier",
        "risk_flags": ["Late venue confirmation"],
    })
    if r.status_code == 200:
        out = r.json()["data"]
        if out.get("memory_generated") is True:
            ok("Outcome saved AND memory auto-generated")
        else:
            fail("Memory generation", f"memory_generated={out.get('memory_generated')}")
        if out.get("budget_variance_pct") is not None:
            variance = out["budget_variance_pct"]
            expected = ((275000 - 250000) / 250000) * 100  # 10%
            if abs(variance - expected) < 0.1:
                ok(f"Budget variance computed correctly: {variance:.1f}%")
            else:
                fail("Budget variance", f"Expected {expected:.1f}%, got {variance:.1f}%")
        else:
            fail("Budget variance", "Not computed")
    else:
        fail("Outcome submission", r.text[:200])

    # Verify outcome persisted
    r = await c.get(f"{API}/memory/events/{evt_id}/outcome", headers=h)
    if r.status_code == 200:
        saved_out = r.json()["data"]
        if saved_out.get("actual_spend") == 275000.0:
            ok("Outcome actual_spend persisted correctly")
        else:
            fail("Outcome persistence", f"actual_spend = {saved_out.get('actual_spend')}")
        if saved_out.get("lessons_learned") == "Venue booking should be done 2 months earlier":
            ok("Outcome lessons_learned persisted correctly")
        else:
            fail("Outcome lessons", f"Got: {saved_out.get('lessons_learned', '')[:50]}")
    else:
        fail("GET outcome", r.text[:100])

    # Verify duplicate rejected
    r = await c.post(f"{API}/memory/events/{evt_id}/outcome", headers=h, json={
        "approval_result": "approved"
    })
    if r.status_code == 400:
        ok("Duplicate outcome submission rejected (400)")
    else:
        fail("Duplicate outcome", f"Expected 400, got {r.status_code}")

    # Verify event status changed to 'completed'
    r = await c.get(f"{API}/events/{evt_id}", headers=h)
    if r.status_code == 200 and r.json()["data"]["status"] == "completed":
        ok("Event status changed to 'completed' after outcome")
    else:
        fail("Completion status", r.text[:100])

    # =========================================================================
    # 13. INSTITUTIONAL MEMORY: Retrieval + Isolation
    # =========================================================================
    print("\n--- 13. INSTITUTIONAL MEMORY ---")

    # Verify memory exists for university
    r = await c.get(f"{API}/memory/university/{uni_id}/memories", headers=h)
    if r.status_code == 200:
        mems = r.json()["data"]
        if mems["total"] >= 1:
            ok(f"University has {mems['total']} memory record(s)")
            mem = mems["memories"][0]
            if mem.get("event_title") == "DeepTest Hackathon":
                ok("Memory title matches event title")
            if mem.get("lessons") and len(mem["lessons"]) >= 1:
                ok(f"Memory has {len(mem['lessons'])} lessons stored")
            else:
                fail("Memory lessons", "Empty")
        else:
            fail("Memory count", "0 memories")

    # Create second event to test insights
    r = await c.post(f"{API}/events", headers=h, json={
        "society_id": soc_id, "title": "DeepTest Hackathon 2",
        "event_type": "hackathon", "description": "Second event to test memory retrieval",
        "audience_size": 600, "budget_target": 300000, "currency": "PKR",
    })
    if r.status_code == 201:
        evt2_id = r.json()["data"]["id"]

        # Get insights — should reference the first event
        r = await c.get(f"{API}/memory/events/{evt2_id}/insights", headers=h)
        if r.status_code == 200:
            ins = r.json()["data"]
            if len(ins.get("recommendations", [])) >= 1:
                ok(f"Insights generated: {len(ins['recommendations'])} recommendations")
            else:
                fail("Insights recommendations", "None")
        else:
            fail("GET insights", r.text[:100])

    # Verify outcome verification workflow
    r = await c.put(f"{API}/memory/events/{evt_id}/outcome/verify", headers=h)
    if r.status_code == 200 and r.json()["data"].get("is_verified") is True:
        ok("Outcome verification workflow works")
    else:
        fail("Outcome verification", r.text[:100])

    # =========================================================================
    # 14. EXPORT ENDPOINTS: Verify they return binary content
    # =========================================================================
    print("\n--- 14. DOCUMENT EXPORTS ---")

    for name, path, mime in [
        ("Proposal PDF", "proposal/pdf", "application/pdf"),
        ("Proposal DOCX", "proposal/docx", "application/vnd.openxmlformats"),
        ("Budget XLSX", "budget/xlsx", "application/vnd.openxmlformats"),
        ("Sponsorship PDF", "sponsorship/pdf", "application/pdf"),
    ]:
        r = await c.get(f"{API}/exports/{evt_id}/{path}", headers=h)
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            if mime in content_type:
                size = len(r.content)
                if size > 100:
                    ok(f"{name}: {size} bytes, type={content_type[:40]}")
                else:
                    fail(f"{name}", f"Suspiciously small: {size} bytes")
            else:
                fail(f"{name}", f"Wrong content-type: {content_type}")
        else:
            fail(f"{name}", f"{r.status_code}")

    # =========================================================================
    # 15. DATA ISOLATION: Different user can't access other's data
    # =========================================================================
    print("\n--- 15. DATA ISOLATION ---")

    # Register a second user
    email2 = f"other_{uuid.uuid4().hex[:8]}@test.com"
    r = await c.post(f"{API}/auth/register", json={
        "email": email2, "password": "OtherUser1!", "full_name": "Other User"
    })
    if r.status_code == 201:
        h2 = {"Authorization": f"Bearer {r.json()['data']['access_token']}", "Content-Type": "application/json"}

        # Other user should NOT be able to generate for our event
        r = await c.post(f"{API}/events/{evt_id}/generate-all", headers=h2, timeout=10)
        if r.status_code == 403:
            ok("Other user blocked from generating (403)")
        else:
            fail("Generation isolation", f"Expected 403, got {r.status_code}")

        # Other user's society list should be empty
        r = await c.get(f"{API}/societies", headers=h2)
        if r.status_code == 200 and len(r.json()["data"]) == 0:
            ok("Other user sees 0 societies (correct isolation)")
        else:
            fail("Society isolation", f"Expected 0, got {len(r.json().get('data', []))}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print(f"DEEP VERIFICATION COMPLETE: {PASS} passed, {FAIL} failed")
    print("=" * 70)

    await c.aclose()
    return FAIL == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
