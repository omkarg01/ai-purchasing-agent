# Problem Discovery & Engineering Thinking

## AI-Powered Purchasing Agent

### 1. Understanding the business problem

Before thinking about implementation, I first tried to understand the actual business problem this system was expected to solve.

I approached the problem through three questions:

**What problem does the purchasing team experience?**

Purchasing teams need to review multiple factors before making purchasing decisions. This takes time and creates opportunities for unnecessary purchases, excess inventory and inefficient spending.

The objective is not simply to automate purchase order creation. It is to improve the quality, efficiency and reliability of purchasing decisions.

**What decisions does a purchasing team need to make?**

The purchasing process involves several decisions:

- Whether a product needs to be purchased.
- How much inventory should be ordered.
- When the purchase should happen.
- Which supplier should fulfil the requirement.
- Whether the supplier can meet the required delivery timeline.
- Whether the purchase satisfies budget and operational constraints.

**What can go wrong if an AI system makes an incorrect decision?**

An incorrect purchasing decision can result in:

- Unnecessary inventory and wasted spending.
- Insufficient inventory and potential stockouts.
- Delayed deliveries due to supplier constraints.
- Budget overruns.
- Inventory and storage constraints.

This helped establish that the system needs to investigate, evaluate and justify purchasing decisions rather than simply generate recommendations.

### 2. Understanding the problem through a practical scenario

I used a sample purchasing scenario to understand how inventory, demand and supplier information influence a decision.

| Parameter | Value |
|---|---:|
| Current inventory | 300 units |
| Expected demand over 14 days | 900 units |
| Existing open purchase order | 400 units |
| Supplier lead time | 5 days |
| Recommended purchase quantity | 800 units |
| Available budget | ₹50,000 |

The first question was whether the recommendation to purchase 800 units was actually justified.

A basic inventory-position calculation gives:

Current inventory + Existing open PO = 300 + 400 = 700 units.

Compared with expected demand of 900 units, this suggests a projected shortage of 200 units over the 14-day period.

However, this calculation alone is insufficient to determine the purchasing quantity.

I identified additional information that could influence the decision:

- Actual expected delivery date of the existing purchase order.
- Supplier delivery reliability.
- Unit purchase price.
- Available storage capacity.
- Minimum order quantity (MOQ).
- Safety stock requirements.

### 3. Understanding inventory timing and stockout risk

One important observation was that inventory availability must be evaluated over time, not only through total quantities.

Using the simplified assumption of evenly distributed demand:

Average daily demand = 900 / 14 ≈ 64 units.

Estimated inventory coverage = 300 / 64 ≈ 4.7 days.

With a supplier lead time of five days, the existing inventory could run out before a new order arrives.

This exposed an important distinction:

A purchasing decision may be sufficient to meet total forecast demand but still fail to prevent a stockout because replenishment arrives too late.

Therefore, the agent needs to evaluate delivery timing and potential stockout risk before recommending an action.

### 4. Exploring possible recovery actions

Rather than immediately creating another purchase order, I considered possible actions the system could investigate:

1. Recalculate inventory risk using demand and delivery timing.
2. Contact the existing supplier to investigate earlier or partial delivery.
3. Investigate alternative suppliers for emergency stock.
4. Escalate decisions requiring human intervention or approval.

I also recognised that alternative supplier investigation could happen in parallel with contacting the existing supplier, rather than waiting until the existing supplier fails.

The key distinction is between investigating an option and committing to a purchase.

### 5. Important assumptions and lessons

During the analysis, I identified several assumptions that should not be treated as facts:

- An open purchase order is not necessarily guaranteed inventory.
- A new purchase order does not automatically solve an immediate stockout risk.
- A safety stock percentage should not be arbitrarily selected.
- A lower purchase price does not automatically justify increasing inventory.
- An LLM-generated confidence percentage does not necessarily represent the actual probability of a correct decision.

I also identified the need to distinguish between data reliability, decision confidence and the authority to execute a purchasing action.

### 6. Initial engineering direction

Based on this exploration, I concluded that the application should behave as a decision-support and execution system.

Its core workflow should be:

**Investigate → Evaluate → Decide → Approve → Execute → Validate**

The system should:

- Gather relevant purchasing information.
- Apply deterministic business rules and calculations.
- Use an LLM to coordinate investigation and explain decisions.
- Recommend an appropriate action with supporting evidence.
- Obtain human approval before consequential purchasing actions.
- Validate that the executed action produced the expected result.

### 7. Scope of the initial implementation

Given the limited development time, I decided to prioritise one complete end-to-end purchasing scenario rather than implementing every possible scenario superficially.

The initial implementation will demonstrate how the system evaluates a purchasing recommendation, identifies constraints, makes a decision, executes an approved action and validates the outcome.

This document captures the initial problem-discovery process. The architecture, data model and implementation decisions will be documented separately as the system evolves.