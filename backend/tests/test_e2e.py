"""End-to-end test of the complete SocietyOS user journey (16 steps)."""

import asyncio
import sys
import uuid

import httpx

API = "http://localhost:8000/api/v1"
TIMEOUT = 30


class E2ETest:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.token = None
        self.user_id = None
        self.university_id = None
        self.society_id = None
        self.event_id = None
        self.policy_id = None
        self.results = []

    def h(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def step(self, num, name, func):
        try:
            await func()
            self.results.append((num, name, "PASS", ""))
            print(f"  PASS  Step {num}: {name}")
        except Exception as e:
            self.results.append((num, name, "FAIL", str(e)))
            print(f"  FAIL  Step {num}: {name} -- {e}")

    async def run(self):
        print("=" * 60)
        print("SocietyOS AI — E2E Test Suite")
        print("=" * 60)

        await self.step(1, "Register user", self._register)
        await self.step(2, "Create society", self._create_society)
        await self.step(3, "Configure profile", self._configure_profile)
        await self.step(4, "Create event (NL)", self._create_event)
        await self.step(5, "Submit policy", self._submit_policy)
        await self.step(6, "Review policy", self._review_policy)
        await self.step(7, "Generate package", self._generate_package)
        await self.step(8, "Review proposal", self._review_proposal)
        await self.step(9, "Review budget", self._review_budget)
        await self.step(10, "Review sponsorship", self._review_sponsorship)
        await self.step(11, "Review approvals", self._review_approvals)
        await self.step(12, "Manage tasks", self._manage_tasks)
        await self.step(13, "Dashboard", self._load_dashboard)
        await self.step(14, "Share event", self._share_event)
        await self.step(15, "Enter outcomes", self._enter_outcomes)
        await self.step(16, "Verify memory", self._verify_memory)

        print("\n" + "=" * 60)
        passed = sum(1 for r in self.results if r[2] == "PASS")
        failed = sum(1 for r in self.results if r[2] == "FAIL")
        print(f"Results: {passed} passed, {failed} failed out of {len(self.results)}")
        print("=" * 60)
        if failed:
            print("\nFailed:")
            for num, name, status, err in self.results:
                if status == "FAIL":
                    print(f"  Step {num} ({name}): {err[:200]}")
        await self.client.aclose()
        return failed == 0

    async def _register(self):
        email = f"e2e_{uuid.uuid4().hex[:8]}@test.com"
        resp = await self.client.post(f"{API}/auth/register", json={
            "email": email, "password": "TestPass123!", "full_name": "E2E Test User"
        })
        assert resp.status_code == 201, f"Register: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        self.token = data["access_token"]

    async def _create_society(self):
        # Create university
        resp = await self.client.post(f"{API}/universities", headers=self.h(), json={
            "name": f"E2E Uni {uuid.uuid4().hex[:6]}", "city": "Lahore", "country": "Pakistan"
        })
        assert resp.status_code == 201, f"Uni: {resp.status_code} {resp.text[:200]}"
        self.university_id = resp.json()["data"]["id"]

        # Create society
        resp = await self.client.post(f"{API}/societies", headers=self.h(), json={
            "name": "E2E Tech Society", "university_id": self.university_id,
            "department": "Computer Science", "society_type": "technical",
        })
        assert resp.status_code == 201, f"Society: {resp.status_code} {resp.text[:200]}"
        self.society_id = resp.json()["data"]["id"]

    async def _configure_profile(self):
        resp = await self.client.put(f"{API}/societies/{self.society_id}", headers=self.h(), json={
            "faculty_advisor_name": "Dr. Ahmed Khan",
            "faculty_advisor_email": "ahmed@uni.edu",
            "description": "Leading tech society",
            "approval_chain": {"steps": [
                {"order": 1, "authority": "Dr. Ahmed Khan", "role": "faculty_advisor"},
                {"order": 2, "authority": "Head of CS", "role": "hod"},
                {"order": 3, "authority": "Dean", "role": "dean"},
            ]}
        })
        assert resp.status_code == 200, f"Profile: {resp.status_code} {resp.text[:200]}"

    async def _create_event(self):
        # Parse NL
        resp = await self.client.post(f"{API}/events/parse", headers=self.h(), json={
            "description": "2-day hackathon CodeFest 2026, March 15, budget 300000 PKR, 400 students",
            "society_id": self.society_id,
        })
        assert resp.status_code == 200, f"Parse: {resp.status_code} {resp.text[:200]}"

        # Create
        resp = await self.client.post(f"{API}/events", headers=self.h(), json={
            "society_id": self.society_id, "title": "CodeFest 2026",
            "event_type": "hackathon", "description": "Annual hackathon",
            "audience_size": 400, "event_date": "2027-03-15", "duration_days": 2,
            "venue_type": "Main Auditorium", "budget_target": 300000, "currency": "PKR",
        })
        assert resp.status_code == 201, f"Event: {resp.status_code} {resp.text[:200]}"
        self.event_id = resp.json()["data"]["id"]

    async def _submit_policy(self):
        resp = await self.client.post(f"{API}/policy/questionnaire", headers=self.h(), json={
            "university_id": self.university_id,
            "faculty_advisor": "Dr. Ahmed Khan",
            "department": "Computer Science",
            "reports_to": "student_affairs",
            "previous_events": "We organized a hackathon last year, started approval 6 weeks before",
            "past_rejections": "Once rejected for missing budget breakdown",
        })
        assert resp.status_code == 201, f"Policy: {resp.status_code} {resp.text[:200]}"
        self.policy_id = resp.json()["data"]["id"]

    async def _review_policy(self):
        resp = await self.client.get(f"{API}/policy/{self.policy_id}", headers=self.h())
        assert resp.status_code == 200, f"Policy: {resp.status_code} {resp.text[:200]}"

    async def _generate_package(self):
        resp = await self.client.post(
            f"{API}/events/{self.event_id}/generate-all", headers=self.h(), timeout=180,
        )
        assert resp.status_code == 200, f"Generate: {resp.status_code} {resp.text[:200]}"

    async def _review_proposal(self):
        resp = await self.client.get(f"{API}/events/{self.event_id}/proposal", headers=self.h())
        assert resp.status_code == 200, f"Proposal: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        assert "sections" in data
        # Edit
        sections = data["sections"]
        sections["executive_summary"] = sections.get("executive_summary", "") + " [edited]"
        resp = await self.client.put(f"{API}/events/{self.event_id}/proposal", headers=self.h(),
                                     json={"sections": sections})
        assert resp.status_code == 200, f"Edit proposal: {resp.status_code}"

    async def _review_budget(self):
        resp = await self.client.get(f"{API}/events/{self.event_id}/budget", headers=self.h())
        assert resp.status_code == 200, f"Budget: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        assert "categories" in data

    async def _review_sponsorship(self):
        resp = await self.client.get(f"{API}/events/{self.event_id}/sponsorship", headers=self.h())
        assert resp.status_code == 200, f"Sponsorship: {resp.status_code} {resp.text[:200]}"

    async def _review_approvals(self):
        resp = await self.client.get(f"{API}/events/{self.event_id}/approvals", headers=self.h())
        assert resp.status_code == 200, f"Approvals: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        assert len(data) >= 2
        step_id = data[0]["id"]
        resp = await self.client.put(f"{API}/events/{self.event_id}/approvals/{step_id}",
                                     headers=self.h(), json={"status": "submitted"})
        assert resp.status_code == 200

    async def _manage_tasks(self):
        resp = await self.client.post(f"{API}/events/{self.event_id}/tasks", headers=self.h(),
                                      json={"title": "E2E task", "team": "QA", "priority": "high",
                                            "due_date": "2027-03-10"})
        assert resp.status_code == 200, f"Task: {resp.status_code} {resp.text[:200]}"
        tid = resp.json()["data"]["id"]
        resp = await self.client.put(f"{API}/events/{self.event_id}/tasks/{tid}",
                                     headers=self.h(), json={"status": "in_progress"})
        assert resp.status_code == 200

    async def _load_dashboard(self):
        resp = await self.client.get(f"{API}/events/{self.event_id}/dashboard", headers=self.h())
        assert resp.status_code == 200, f"Dashboard: {resp.status_code}"
        data = resp.json()["data"]
        assert "event" in data and "approvals" in data and "tasks" in data

    async def _share_event(self):
        resp = await self.client.post(f"{API}/events/{self.event_id}/share", headers=self.h())
        assert resp.status_code == 200
        token = resp.json()["data"]["token"]
        resp = await self.client.get(f"{API}/shared/{token}")
        assert resp.status_code == 200
        assert resp.json()["data"]["read_only"] is True

    async def _enter_outcomes(self):
        resp = await self.client.post(f"{API}/memory/events/{self.event_id}/outcome",
                                      headers=self.h(), json={
                                          "approval_result": "approved",
                                          "actual_approval_days": 18,
                                          "actual_spend": 320000,
                                          "overspent_categories": ["Catering"],
                                          "actual_audience": 450,
                                          "sponsors_pitched": 12,
                                          "sponsors_confirmed": 5,
                                          "lessons_learned": "Catering exceeded estimates by 25%",
                                          "risk_flags": ["Late venue confirmation"],
                                      })
        assert resp.status_code == 200, f"Outcome: {resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        assert data.get("memory_generated") is True

    async def _verify_memory(self):
        # Create second event
        resp = await self.client.post(f"{API}/events", headers=self.h(), json={
            "society_id": self.society_id, "title": "CodeFest 2027",
            "event_type": "hackathon", "description": "Second hackathon",
            "audience_size": 500, "budget_target": 350000, "currency": "PKR",
        })
        assert resp.status_code == 201
        event2_id = resp.json()["data"]["id"]

        # Insights
        resp = await self.client.get(f"{API}/memory/events/{event2_id}/insights", headers=self.h())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "recommendations" in data and "insights" in data

        # University memories
        resp = await self.client.get(f"{API}/memory/university/{self.university_id}/memories",
                                     headers=self.h())
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] >= 1

        # Verify outcome
        resp = await self.client.put(f"{API}/memory/events/{self.event_id}/outcome/verify",
                                     headers=self.h())
        assert resp.status_code == 200


async def main():
    test = E2ETest()
    success = await test.run()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
