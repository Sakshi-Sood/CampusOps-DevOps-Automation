# CampusOps acceptance checklist

Use this checklist throughout implementation. Checked items have evidence in the stated environment. For each run, record the date and time zone, app revision, environment, AWS region if applicable, result, and evidence location. Use synthetic data and redact secrets, student details, account identifiers, and private key material from evidence.

## Phase 2: Application

| Check | Requirements | Procedure and expected result |
| --- | --- | --- |
| [x] AT-01 Event catalog | FR-01 | Open the event listing and a detail page. Each seeded event shows its title, schedule with time zone, venue, description, and a path to registration. An unknown detail page returns 404. |
| [x] AT-02 Registration and confirmation | FR-02, FR-05, FR-06 | Submit one valid registration. Confirm the browser redirects only after the row is stored. The final page identifies the event, contains no attendee details, and creates no extra records when refreshed. |
| [x] AT-03 Invalid input | FR-02, FR-03, NFR-01 | Submit a missing name, an overlong name, a malformed or overlong email, a missing or invalid CSRF token, and an unknown event ID. Each is rejected and the row count stays unchanged. |
| [x] AT-04 Duplicates | FR-04 | Submit an email, then try a case or whitespace variant for the same event. The second registration is rejected. Repeat with two simultaneous submissions into a fresh fixture and confirm exactly one write. The same email can register for another event. |
| [x] AT-05 Persistence and health | FR-05, FR-07 | With an isolated test database, save a registration and restart the app. Verify the row remains and `/health` returns 200. Independently point the test app at an unavailable and an uninitialized database and verify 503 without internal details. |
| [x] AT-06 Usability | NFR-04 | Check an event page and form at 360 px. Verify there is no horizontal scroll, every input has a label, focus is visible, and the form can be completed with a keyboard. Trigger an error and verify it is clear and associated with the field. |

### Local verification evidence

| Check | Evidence |
| --- | --- |
| AT-01 | Flask tests verified the seeded listing, schedule, venue, description, registration path, and unknown-event 404. Catalog and detail pages were inspected in Chrome. |
| AT-02 | A valid POST returned 303 after the row was saved. The confirmation page showed the event without attendee details. Refresh did not add another row. |
| AT-03 | Flask tests verified rejected names, emails, event IDs, and CSRF tokens without database writes. The validation message and retained field were also checked in Chrome. |
| AT-04 | Case and whitespace variants returned 409 for the same event. Concurrent requests produced one 303, one 409, and one row. The same email registered successfully for a different event. |
| AT-05 | An isolated registration survived recreating the Flask app. Tests and loopback HTTP checks verified 200 for initialized SQLite and generic 503 for unavailable and uninitialized SQLite. |
| AT-06 | Earlier Chrome checks covered the detail page and registration form at 360 px. Verified no horizontal overflow, associated labels and errors, visible keyboard focus, and keyboard submission. |

The full local pytest suite passed with 53 cases. Application readiness was verified directly over loopback. Deployment, Nginx/Gunicorn integration, Nagios checks, and deployed performance remain pending.

## Phases 3 and 4: Infrastructure and deployment

| Check | Requirements | Procedure and expected result |
| --- | --- | --- |
| [ ] AT-07 Pre-launch review | FR-08, NFR-07, NFR-08 | Check account plan, eligible services and AMI, region, credit balance, expiry, expected runtime, and cost. Show the planned resource set and Terraform plan. Confirm that work stops at the approval checkpoint when approval has not been given. |
| [ ] AT-08 Provisioning | FR-08, NFR-01 | After approval, verify two tagged Ubuntu instances, two encrypted gp3 root volumes, IMDSv2, two automatically assigned public IPv4 addresses, a VPC, a public subnet, an internet gateway, a route table and subnet association, two security groups, and the registered public key. Compare named Terraform outputs with the instance addresses. |
| [ ] AT-09 Network boundaries | FR-09, FR-10, NFR-01 | Verify operator SSH with known host fingerprints, an allowed viewer's web connection, a denial from an authorized test source outside the allowlist, and private checks from the monitoring host. Verify the Nagios UI opens through the tunnel and has no direct ingress. Confirm the metrics identity can collect metrics and cannot request a shell or forwarding. |
| [ ] AT-10 Deploy and redeploy | FR-05, FR-09, NFR-02 | With approval, deploy from the recorded revision. Verify Nginx configuration, Gunicorn service status, health through Nginx, and a successful registration. Redeploy with approval and confirm the existing row survives. |
| [ ] AT-11 Idempotency | FR-09, NFR-03 | Run a fresh Terraform plan on unchanged resources and expect no resource changes. With approval, rerun Ansible on unchanged hosts and expect `changed=0` and no failed tasks. Capture summaries and the deployed revision. |
| [ ] AT-12 Lab performance | NFR-05 | Against a warmed deployment, submit 20 unique synthetic registrations using up to five concurrent permitted clients. Record test location, instance type, response latency, errors, and SQLite row count. All 20 writes succeed and p95 request-to-confirmation is at or below 2 seconds. |

## Phases 5 to 7: Monitoring, workflow, and cleanup

| Check | Requirements | Procedure and expected result |
| --- | --- | --- |
| [ ] AT-13 Check coverage | FR-07, FR-10 | Validate Nagios configuration and exercise TCP reachability, private HTTP health, CPU, memory, and database filesystem disk checks. Test the custom latency plugin against a controlled slow response in a test fixture. Verify normal checks report OK and threshold breaches produce the expected state. |
| [ ] AT-14 Outage and problem notification | FR-11, NFR-06, NFR-08 | With approval, stop Gunicorn and leave Nginx active. Verify the portal fails, Nagios confirms a hard HTTP failure within two minutes, and the approved inbox receives a problem email. Record mail delivery separately from monitoring detection. |
| [ ] AT-15 Recovery and recovery notification | FR-05, FR-11, NFR-06 | Inspect the check result and service logs. With approval, rerun Ansible to restore Gunicorn. Confirm health returns 200, the original registration persists, and a new registration succeeds. Nagios returns to OK within two minutes of restored health and the inbox receives a recovery email. A subsequent approved Ansible run meets AT-11. |
| [ ] AT-16 One-command workflow | FR-09, FR-12, NFR-03, NFR-08 | Run the shell entry point in an approved demo. Confirm it shows its plan and cost, honors both approval checkpoints, generates inventory with public management addresses and the private app target, waits for SSH, deploys, and verifies app and monitor. Exercise a malformed output or SSH failure using a local fixture and confirm downstream stages stop. |
| [ ] AT-17 Backup and teardown | FR-13, NFR-07, NFR-08 | Export and restore synthetic data in an isolated test before teardown. Confirm the correct AWS identity, region, and state. Show the saved destroy plan and wait for separate approval. After approval, verify the lab instances, root volumes, public addresses, and network are gone. Record deliberately retained resources and check Billing after it updates. |

## Phase 8: Documentation and demonstration

| Check | Requirements | Procedure and expected result |
| --- | --- | --- |
| [ ] AT-18 Reproduction and publication | NFR-02, NFR-03, NFR-08 | Follow the README and runbooks from a clean checkout. Confirm they identify versions, environment requirements, deployment and recovery paths, known limitations, and evidence. Verify sensitive artifacts are ignored. Show staged changes and wait before each commit. Show remote, branch, outgoing commits, and summary and wait before each push. |
| [ ] AT-19 Operational explanation | NFR-02, NFR-03 | Demonstrate one request, the Terraform-to-Ansible handoff, Nagios hard-state transition, recovery, and cost review. Explain how the evidence proves persistence, idempotency, alert delivery, and verified cleanup. |

## Evidence template

| Check | Environment and revision | Expected | Observed | Result and evidence |
| --- | --- | --- | --- | --- |
| AT-__ | | | | Pending |

For the incident demonstration, record the service-stop time, first failed check, hard-state time, problem email arrival, recovery action, first healthy HTTP result, Nagios OK time, and recovery email arrival. This separates detection latency from mail delivery latency.
