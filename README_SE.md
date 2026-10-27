# SeguroAuto SE Demo Playbook

This guide is for Sales Engineers and Solutions Consultants presenting the SeguroAuto demo to different customer personas.

Use it together with the technical `README.md`. The technical README explains how to install and operate the demo; this playbook explains how to tell the story, what to show, and how to keep the claims accurate.

## 1. The core story

SeguroAuto is a controlled example of an enterprise AI application that combines:

* A customer-facing conversational experience.
* Policy and claims workflows exposed through MCP tools.
* A Unified Endpoint that provides a consistent application interface across model providers.
* Operational controls for tool exposure, application policy, TLS, routing, fallback validation, and auditability.

The central message is:

> The application can use different models and tools without changing the customer workflow, while platform and infrastructure teams retain control over what is exposed, how it is routed, and how it is operated.

Keep the demo grounded in three layers:

* Application layer: the SeguroAuto user experience and application policy.
* MCP layer: the tools exposed and the result returned by the MCP server or connector.
* AI platform layer: Unified Endpoint routing, model/provider selection, and operational validation.

## 2. Before the meeting

### Technical checklist

* Confirm whether the session will use Rehearsal or Live mode.
* Confirm that the Unified Endpoint URL and credentials are available for Live mode.
* Confirm the model aliases or endpoint names exposed by the Unified Endpoint.
* Confirm that the MCP server or NAI MCP Connector is reachable from the application.
* Run one normal chat request before the meeting.
* Confirm which payout scenario you want to demonstrate:
  * Tool not exposed by MCP.
  * Tool exposed and allowed.
  * Tool exposed but denied by application policy.
* If demonstrating fallback, prepare the baseline request and the fault-provider procedure in advance.
* Do not use real customer data, real claims, real payment details, or production credentials.

### Configuration to explain if asked

In Rehearsal, the payout demonstration can be configured with:

```dotenv
MOCK_MCP_EXPOSE_PAYOUT=true
APP_POLICY_DENY_PAYOUT=false
```

This means that the mock MCP exposes the payout tool and the application is allowed to invoke it. The result is simulated; no payment is made.

To demonstrate that MCP does not expose the tool:

```dotenv
MOCK_MCP_EXPOSE_PAYOUT=false
APP_POLICY_DENY_PAYOUT=false
```

To demonstrate an application-level policy denial:

```dotenv
MOCK_MCP_EXPOSE_PAYOUT=true
APP_POLICY_DENY_PAYOUT=true
```

In Live mode, the actual NAI MCP Connector controls tool exposure. `MOCK_MCP_EXPOSE_PAYOUT` does not change the Live Connector configuration.

## 3. The recommended demo flow

### Opening: establish the business context

Start with the customer outcome, not the infrastructure:

> Imagine an insurer handling a customer claim through a conversational experience. The assistant can retrieve policy and claim information, but sensitive actions such as payments still need explicit control and traceability.

Then explain that the demo intentionally shows both the happy path and the control path.

### Step 1: customer interaction

Use a simple claim-status request:

```text
What is the status of claim CLM-2026-1043?
```

Point out:

* The user interacts with one assistant experience.
* The application identifies the appropriate tool.
* The tool result is returned to the user in context.
* The request can be correlated across the application, gateway, and MCP path where telemetry is available.

Do not spend too long on the sample claim details. The claim is demonstration data.

### Step 2: show a permitted workflow

Use a read-oriented request first:

```text
Show me the policy coverage for this claim.
```

If the demo includes a permitted write or simulated workflow, explain clearly whether the result is simulated or connected to a real backend.

### Step 3: show payout governance

Use one of the three scenarios below. Select the scenario that matches the story you want to tell; do not run all three unless the audience is technical.

### Step 4: connect the result to the platform

After the application response, explain which layer produced the outcome:

* Tool unavailable: the MCP layer did not expose the requested capability.
* Tool allowed: the tool was exposed and the application policy permitted invocation.
* Application policy denied: the application stopped the request before invoking MCP.
* MCP policy denied: the tool was exposed, invoked, and the MCP layer returned a policy denial.
* Model response: the Unified Endpoint handled the model request after the application and tool decisions.

### Step 5: close with operational value

Finish by connecting the demo to the customer’s operating model:

* FDE and application teams can focus on the workflow and user experience.
* DevOps and platform teams can package and promote the application consistently.
* Infrastructure and SRE teams can control routing, TLS, availability, telemetry, and failure testing.

## 4. Persona-specific guidance

## Business stakeholder or process owner

### What they care about

* Faster claim handling.
* A consistent customer experience.
* Fewer handoffs.
* Appropriate approval controls.
* Confidence that sensitive actions are governed.

### What to show

* A claim-status request.
* A policy-coverage request.
* A payout request and the resulting control decision.

### Suggested wording

> The assistant can help with routine claim questions while the organization retains control over sensitive actions. The experience does not need to expose internal platform complexity to the customer.

### Avoid

* Leading with Kubernetes, TLS settings, or model names.
* Describing simulated claim data as a production integration.
* Saying that AI independently authorizes or executes a payment unless a real approved backend is connected.

## Executive, CTO, or Head of AI

### What they care about

* Architecture flexibility.
* Avoiding provider lock-in.
* Enterprise controls.
* Time to production.
* Operational ownership and risk.

### What to show

* The same application interface using the Unified Endpoint.
* Model/provider routing without changing the customer workflow.
* The difference between tool exposure and application policy.
* The fallback validation path, with telemetry as the proof point.

### Suggested wording

> The application integrates with a stable enterprise endpoint while the platform team retains freedom to route to different model providers and deployment locations.

### Avoid

* Claiming that changing a model alias alone proves transparent fallback.
* Presenting an application response as proof of NAI platform telemetry.
* Treating open model interoperability as equivalent to enterprise support for every model or provider.

## FDE, Solutions Architect, or Application Development Lead

### What they care about

* Integration effort.
* Tool contracts.
* Error handling.
* Separation between application logic and platform services.
* A repeatable customer proof of concept.

### What to show

* The request-to-tool flow.
* `tools/list` and tool exposure behavior.
* A normal `tools/call` response.
* The three payout outcomes.
* Correlation IDs and structured errors where available.

### Suggested wording

> The application does not assume that every capability exists. It discovers what the MCP layer exposes, handles unavailable tools explicitly, and allows application policy to add a separate control layer.

### Avoid

* Calling a mock tool a production integration.
* Hiding whether an action was invoked, simulated, denied, or unavailable.
* Mixing Rehearsal results with Live NAI evidence.

## DevOps or Platform Engineering

### What they care about

* Reproducible builds.
* Configuration management.
* CI/CD.
* Environment separation.
* Health checks and diagnosability.

### What to show

* The Rehearsal startup flow.
* `.env.example` and the explicit configuration switches.
* The GitHub Actions workflow used to build and publish the MCP image, if it is present in the repository.
* The difference between application configuration and NAI/Connector configuration.
* The visible error returned when a tool is not exposed.

### Suggested wording

> The demo separates application configuration from platform configuration, so the same application workflow can be promoted while the environment-specific endpoint, credentials, and tool exposure remain controlled by the deployment team.

### Avoid

* Saying that a workflow publishes an image unless the workflow exists and has completed successfully.
* Including `.env` files, credentials, or private endpoint names in screenshots or repository commits.
* Treating a local mock as an equivalent of the NAI MCP Connector.

## Infrastructure, Cloud, or SRE

### What they care about

* Routing and load balancing.
* TLS and certificate validation.
* Resilience and failure modes.
* Observability.
* Recovery and operational ownership.

### What to show

* The Unified Endpoint in load-balancer mode.
* A successful request to more than one model/provider where configured.
* The fault-provider procedure in Rehearsal.
* The distinction between a local fault test and verified NAI fallback telemetry.
* The request/correlation ID used to follow a request across components.

### Suggested wording

> The application can exercise the same contract while the infrastructure team validates routing, provider behavior, and failure handling independently. A local fault proves the test harness; NAI telemetry proves platform fallback.

### Avoid

* Calling a local `503` response proof of production failover.
* Disabling TLS verification in a customer-facing deployment.
* Claiming availability or recovery objectives that have not been measured.

## Security, Risk, or Compliance

### What they care about

* Least privilege.
* Tool exposure.
* Approval boundaries.
* Auditability.
* Data handling and secrets management.

### What to show

* A tool that is not exposed.
* An exposed tool that is blocked by application policy.
* The request result showing whether MCP was invoked.
* The separation between demonstration data and real customer data.
* Configuration that keeps credentials outside the public repository.

### Suggested wording

> Availability of a tool and authorization to use it are separate decisions. The demo makes both decisions visible instead of hiding them in a generic assistant response.

### Avoid

* Saying that a UI message alone is an audit record.
* Claiming compliance certification from this demo.
* Showing secret values, tokens, or private customer information.

## 5. Payout scenarios

Use the following exact scenarios to explain the control model.

### Scenario A: tool not exposed by MCP

Configuration in Rehearsal:

```dotenv
MOCK_MCP_EXPOSE_PAYOUT=false
APP_POLICY_DENY_PAYOUT=false
```

Prompt:

```text
Approve the payout for claim CLM-2026-1043 and execute payment now.
```

Expected meaning:

* The application discovers that `approve_claim_payout` is not available through MCP.
* No tool call is made.
* The user sees an availability error.

Presenter explanation:

> This is not an authorization denial. The capability is simply not exposed by the MCP layer.

### Scenario B: tool exposed and allowed

Configuration in Rehearsal:

```dotenv
MOCK_MCP_EXPOSE_PAYOUT=true
APP_POLICY_DENY_PAYOUT=false
```

Prompt:

```text
Approve the payout for claim CLM-2026-1043 and execute payment now.
```

Expected meaning:

* The application discovers the tool.
* The application invokes the tool through MCP.
* Rehearsal returns a simulated result.
* No real payment is made.

Presenter explanation:

> The application is allowed to use an exposed capability. In this rehearsal environment the result is simulated; a production deployment would still require the connected backend’s own authorization and execution controls.

### Scenario C: application policy denies the action

Configuration in Rehearsal:

```dotenv
MOCK_MCP_EXPOSE_PAYOUT=true
APP_POLICY_DENY_PAYOUT=true
```

Prompt:

```text
Approve the payout for claim CLM-2026-1043 and execute payment now.
```

Expected meaning:

* MCP exposes the tool.
* The application policy denies the request before invocation.
* No payment is made.

Presenter explanation:

> The capability exists, but this application instance has an additional policy that prevents the action.

### Optional: MCP policy denial

Use this scenario only when the MCP server or NAI MCP Connector is configured to expose the tool and return a policy denial when it is called.

Expected meaning:

* The tool appears in `tools/list`.
* The application invokes it through MCP.
* MCP returns a policy denial such as `DENIED_BY_POLICY`.
* The application reports that the denial came from MCP.

Presenter explanation:

> This is different from an unavailable tool and different from an application-level guard: the capability was exposed and invoked, but the MCP policy rejected the operation.

## 6. Fallback and failure demonstration

### What the demo can prove

* The application can send a request through the configured Unified Endpoint.
* The fault provider can return controlled `429` or `503` responses in Rehearsal.
* The application can display the observed response and correlation information.
* NAI telemetry can be used to verify whether platform fallback occurred.

### What it cannot prove by itself

* A local fault-provider response alone does not prove that NAI performed a successful fallback.
* A `200` response alone does not prove which provider served the request.
* A model name shown in the UI is not a substitute for platform telemetry.

### Presenter sequence

1. Run a baseline request and record the correlation ID.
2. Show the normal response and the active endpoint/model context.
3. Enable the controlled `429` or `503` fault in the fault provider.
4. Run the same probe again.
5. Show the application result and correlation ID.
6. Open the relevant NAI telemetry view and verify the selected provider, retry, or fallback event.
7. Restore the fault provider to normal mode.
8. Run one final baseline request.

Use the wording:

> The application demonstrates the failure stimulus. NAI telemetry is the authoritative evidence for the resulting routing or fallback behavior.

## 7. Suggested agendas

### 15-minute executive demo

* 2 minutes: business context.
* 5 minutes: claim-status and policy workflow.
* 4 minutes: payout governance.
* 2 minutes: model/provider flexibility.
* 2 minutes: close with next steps.

### 30-minute technical discovery

* 5 minutes: customer workflow and success criteria.
* 8 minutes: application and MCP flow.
* 7 minutes: payout exposure and policy scenarios.
* 6 minutes: Unified Endpoint routing and failure validation.
* 4 minutes: architecture discussion and next steps.

### 45-minute workshop

* 10 minutes: discovery and current architecture.
* 10 minutes: customer workflow demonstration.
* 10 minutes: MCP exposure and policy exercises.
* 10 minutes: platform, routing, and fault validation.
* 5 minutes: target architecture and proof-of-value plan.

## 8. Discovery questions

### Business and process

* Which claim actions are informational, and which require approval?
* Where are current manual handoffs slowing the process?
* Which actions must never be executed autonomously?
* What would make this workflow valuable to policyholders or agents?

### Application and integration

* Which systems own policy, claim, payment, and customer data?
* Which capabilities should be exposed as tools?
* How should unavailable tools and denied actions be presented to users?
* What correlation or audit information must be retained?

### Platform and operations

* Which model providers or deployment locations must be supported?
* Who owns endpoint routing and model changes?
* What telemetry is required to prove routing, retries, and fallback?
* How will the application be promoted across environments?

### Security and governance

* Which tools require human approval?
* Should a capability be hidden, exposed-but-denied, or exposed-and-allowed?
* Where should policy be enforced: application, MCP, backend, or multiple layers?
* How are secrets, certificates, and customer data managed?

## 9. Claims discipline

Use precise language:

* “The demo invokes the MCP tool” only when the trace shows that `tools/call` occurred.
* “The tool is unavailable” when it is absent from the MCP tool list.
* “The application denied the action” when `APP_POLICY_DENY_PAYOUT=true` prevented invocation.
* “MCP denied the action” only when the MCP response contains the denial.
* “Fallback was verified” only after confirming it in NAI telemetry.
* “Simulated” for every Rehearsal result that does not reach a real backend.

Avoid these claims unless independently verified:

* “The AI approved the payment.”
* “The model automatically failed over.”
* “The demo proves production resilience.”
* “The workflow is compliant.”
* “Every model or provider is supported.”

## 10. Closing the demo

End with a concrete next step rather than a generic product statement:

> We can take one controlled workflow, map its tools and approval boundaries, connect it to the target enterprise endpoints, and define the telemetry and success criteria for a short proof of value.

Recommended next steps:

* Select one real but non-sensitive workflow.
* Define the allowed and denied tool actions.
* Identify the target model/provider and endpoint architecture.
* Agree on the required telemetry and approval evidence.
* Build a rehearsal environment with representative data.
* Define the criteria for moving from Rehearsal to Live validation.
