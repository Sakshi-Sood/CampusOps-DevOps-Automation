# CampusOps requirements

CampusOps demonstrates how a campus event registration portal can be provisioned, deployed, monitored, recovered, and retired repeatably. The design uses a small Flask workload and two AWS EC2 instances. This document defines the requirements for the application and cloud environment.

The primary users are a student registering for an event and an operator deploying and monitoring the demo. Use fictional events and synthetic attendee data throughout the lab. The MVP fixes the event catalog in a seed dataset and collects only a student name and email per registration.

## Functional requirements

All requirements in this table are essential to the MVP.

| ID | Requirement |
| --- | --- |
| FR-01 | Students can browse seeded events and open a detail page showing title, schedule with time zone, venue, description, and a registration action. |
| FR-02 | Students can submit a name and email for an existing event. The server selects the event using its validated identifier and rejects submissions for unknown events. |
| FR-03 | The server trims input, requires a nonempty name up to 100 characters, checks email syntax and a 254-character limit, and rejects missing or invalid CSRF tokens. Invalid requests get an accessible error and create no registration. |
| FR-04 | For the demo, trim and lowercase the email for matching. Enforce one registration per event and normalized email with a SQLite uniqueness constraint. A duplicate produces a clear message and leaves the existing registration intact, including when two requests arrive together. |
| FR-05 | Store a registration ID, event ID, name, normalized email, and creation time in SQLite using parameterized SQL and a transaction. Registrations survive app restart and routine redeployment. |
| FR-06 | After a successful write, redirect to a confirmation page that identifies the event without exposing attendee details in the URL or page. Refreshing the confirmation does not submit the form again. |
| FR-07 | `GET /health` returns HTTP 200 when Flask can read the initialized registration schema and 503 when the database is unavailable or uninitialized. The response is minimal and contains no diagnostic details. A separate registration test exercises writes. |
| FR-08 | Terraform defines the dedicated VPC, public subnet, routing, security groups, SSH public-key registration, and two encrypted Ubuntu EC2 instances. Outputs identify the hosts' management addresses and the app's private monitoring address. |
| FR-09 | Ansible uses an inventory generated from Terraform outputs and verified SSH connections to configure both servers. Install the app, Gunicorn, systemd service, Nginx, and Nagios configuration in the relevant roles. Preserve the database across routine deploys. |
| FR-10 | Nagios Core checks app-host reachability, HTTP health, CPU, available memory, disk usage on the database filesystem, and latency through a custom response-time check. The operator can view states through an SSH tunnel. |
| FR-11 | Nagios sends email on a confirmed failure and on recovery. An operator diagnoses the incident, reruns approved Ansible recovery, and verifies the portal and stored registrations. |
| FR-12 | A WSL shell entry point coordinates planning, approved provisioning, inventory generation, SSH readiness, approved deployment, and smoke tests. A failed stage stops the workflow and identifies the failed step. |
| FR-13 | The operator can review a separate Terraform teardown plan, back up data worth retaining, obtain explicit approval, and verify what remains after destruction. |

## Non-functional requirements

| ID | Category | Requirement |
| --- | --- | --- |
| NFR-01 | Security | Use source-restricted SSH and demo HTTP, verified SSH host keys, a separate restricted monitoring identity, non-root services, encrypted EBS, IMDSv2, and private secret storage. Use only synthetic data over demo HTTP. Require HTTPS before real or public registration. |
| NFR-02 | Maintainability | Use clear directory and role names, versioned configuration, documented tool versions, and one owner for each managed layer. Document deployment, incident recovery, and cleanup. |
| NFR-03 | Reproducibility | Use an identified app revision, dependency pins, Terraform's provider lock file, and generated inventory. A second run on an unchanged deployment produces no Terraform resource changes and no unnecessary Ansible changes. |
| NFR-04 | Usability | The portal supports keyboard form submission, visible focus, associated field labels, recognizable error messages, and a 360 px viewport without horizontal scrolling. |
| NFR-05 | Performance | Lab target: 20 valid registrations with up to five concurrent clients against a warmed deployment, with every write successful and a p95 request-to-confirmation time at or below 2 seconds from a permitted client. Record conditions and results. This target describes the lab exercise. |
| NFR-06 | Monitoring | Use a 60-second normal check interval, 15-second retry interval, and three attempts for the demo HTTP health check. Allow up to two minutes from a controlled service stop to a hard failure and up to two minutes for Nagios to see recovery after health returns. Track mail delivery separately. |
| NFR-07 | Cost | Verify region, plan eligibility, remaining credits, expiry, runtime estimate, and projected usage before any deployment. Keep the baseline to two short-lived hosts and check for residual charges after teardown. |
| NFR-08 | Change control | Show AWS resources, region, estimate, and Terraform plan before deployment and wait for explicit approval. Obtain fresh action-specific approval for AWS modifications and destructive or billable actions. Show staged changes before requesting each commit. Before each push, show the remote, branch, outgoing commits, and change summary and wait for approval. Creating remote repositories, pull requests, or branches also needs approval. |

## Optional enhancements

- Admin dashboard, editable event catalog, capacity and waitlists, student sign-in, and attendee emails.
- Public HTTPS with a registered domain, automated CI validation in GitHub, and a shared Terraform state backend for collaboration.
- Production extensions if demand warrants them include multi-AZ hosting, a load balancer, managed PostgreSQL, and external monitoring.

In the demo, Nagios emails the operator. Registration confirmation is displayed in the browser. One app host and its local database make this a single-instance workload, and the two hosts share one Availability Zone.

See [architecture](architecture.md) for implementation boundaries and [acceptance tests](acceptance-tests.md) for verification.
