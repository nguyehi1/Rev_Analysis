# ASC 606 Revenue Recognition Guide

## Overview

ASC 606 establishes a comprehensive framework for recognizing revenue from contracts with customers. This guide focuses on applying ASC 606 to SaaS subscription contracts.

---

## The Five-Step Model

### Step 1: Identify the Contract(s) with a Customer

**Criteria for a Valid Contract:**
1. The parties have approved the contract and are committed to perform
2. Rights of each party regarding goods/services can be identified
3. Payment terms can be identified
4. The contract has commercial substance
5. Collection of consideration is probable

**For SaaS Contracts:**
- **Verify enforceability**: Check for signatures, legal validity, effective dates
- **Check commercial substance**: Assess if transaction has economic impact
- **Identify payment terms**: Verify payment rights and obligations are clear
- **Multiple contracts assessment**: Determine if related contracts with same customer should be combined
- **Contract modifications**: Identify if this modifies an existing contract (requires separate analysis)

**Red Flags:**
- Missing signatures or dates
- Unclear payment terms
- Party unwilling or unable to pay
- Related contracts that should be combined

**Output:** Pass/Fail determination with reasoning

---

### Step 2: Identify the Performance Obligations in the Contract

**Definition:** A performance obligation is a promise to transfer a distinct good or service (or bundle of goods/services) to the customer.

**Distinctness Criteria (both must be met):**

1. **Capable of being distinct**: Customer can benefit from the good/service on its own or with other readily available resources
2. **Distinct within the context of the contract**: Promise is separately identifiable from other promises

**For SaaS Contracts - Common Performance Obligations:**

| Obligation | Typically Distinct? | Recognition Timing | Rationale |
|------------|-------------------|-------------------|-----------|
| **SaaS Platform Access** | Yes | Over time | Customer simultaneously receives and consumes benefits throughout subscription period |
| **Implementation Services** | Usually Yes | Point in time or Over time | Separately identifiable from SaaS access; no alternative use + enforceable payment right |
| **Data Migration** | Usually Yes | Point in time | Distinct service, typically at contract start |
| **Training** | Usually Yes | Point in time or Over time | Can be provided by other vendors; separately identifiable |
| **Customer Support** | Usually Yes | Over time | Ongoing service throughout support period |
| **Customization/Development** | Depends | Point in time or Over time | May be highly interrelated with SaaS platform |
| **Hosting/Infrastructure** | Usually No | N/A | Typically not distinct from SaaS access |

**Bundling Analysis:**
- Services that are **highly interrelated** or **significantly modify** each other should be bundled
- Consider if vendor is providing a **combined output**
- Example: Custom development that significantly modifies the SaaS platform may be bundled with SaaS access

**Output:** List of distinct performance obligations with classification and rationale

---

### Step 3: Determine the Transaction Price

**Transaction Price Components:**

1. **Fixed Consideration**
   - Base subscription fees
   - One-time fees (setup, implementation)
   - Annual maintenance/support fees

2. **Variable Consideration**
   - Usage-based fees
   - Performance bonuses
   - Penalties/liquidated damages
   - Discounts, rebates, refunds, credits
   - Price concessions

**Estimating Variable Consideration:**

Use one of these methods (whichever better predicts):
- **Expected Value**: Probability-weighted amount (use when many similar contracts)
- **Most Likely Amount**: Single most likely outcome (use when two possible outcomes)

**Constraint on Variable Consideration:**
Include variable consideration only to the extent it is **highly probable** that a significant reversal will not occur when the uncertainty is resolved.

**Factors Increasing Reversal Risk:**
- Amount susceptible to factors outside entity's influence
- Uncertainty not expected to resolve quickly
- Limited experience with similar contracts
- Broad range of possible outcomes
- Entity has history of offering price concessions

**Significant Financing Component:**

Adjust transaction price for time value of money if:
- Timing difference between payment and performance is **>1 year**, AND
- The difference is **significant**

**Practical Expedient:** Don't adjust if period between payment and performance is ≤1 year

**For SaaS Contracts:**
- Annual prepayment: Usually <1 year, no adjustment needed
- Multi-year prepayment: May require adjustment
- Use customer's incremental borrowing rate or vendor's rate

**Other Adjustments:**
- **Non-cash consideration**: Measure at fair value
- **Consideration payable to customer**: Reduce transaction price (unless for distinct good/service)

**Output:** Total transaction price with breakdown and adjustments documented

---

### Step 4: Allocate the Transaction Price to Performance Obligations

**Allocation Method:** Allocate based on **relative standalone selling prices (SSP)**

**Formula:**
```
Allocated Amount = Transaction Price × (SSP of Obligation / Total SSP of All Obligations)
```

**Determining SSP - Hierarchy:**

1. **Observable Price** (preferred)
   - Use actual selling price when sold separately
   - Requires sufficient observable transactions
   - Price must be within a narrow range

2. **Estimate SSP** (if not observable)
   
   Methods:
   - **Adjusted Market Assessment**: Reference competitors' prices for similar goods/services
   - **Expected Cost Plus Margin**: Forecast costs and add appropriate margin
   - **Residual Approach**: Only when SSP is highly variable or uncertain (rare)

**For SaaS Contracts:**

| Obligation | Typical SSP Method | Notes |
|------------|-------------------|-------|
| SaaS Platform | Observable or Market Assessment | Often sold separately; check standalone sales |
| Implementation | Cost Plus Margin | Estimate hours × rate + margin |
| Training | Observable or Cost Plus | Standard training packages may have observable prices |
| Support | Observable | Often sold as renewal after initial term |

**Discount Allocation:**
- If transaction price < sum of SSPs, a discount exists
- Allocate discount **proportionally** to all performance obligations
- **Exception**: Allocate entirely to specific obligations if observable evidence that discount relates only to those

**Variable Consideration Allocation:**
Allocate variable consideration to specific performance obligation (or distinct good/service) if **both** criteria met:
1. Variable payment terms relate specifically to efforts to satisfy that obligation
2. Allocating variable consideration depicts amount expected for satisfying the obligation

Otherwise, allocate to all performance obligations

**Example Allocation:**

```
Transaction Price: $132,000
Performance Obligations:
- SaaS Access: SSP $110,000 → Allocated $108,900 (82.5%)
- Implementation: SSP $25,000 → Allocated $23,100 (17.5%)

Discount: $3,000 ($135,000 SSP - $132,000 actual)
Allocated proportionally: 
- SaaS: $3,000 × 81.5% = $2,445
- Implementation: $3,000 × 18.5% = $555
```

**Output:** Allocation table with SSP, method used, allocated amount, and percentage

---

### Step 5: Recognize Revenue When (or As) Performance Obligations are Satisfied

**Two Recognition Patterns:**

#### A. Over Time Recognition

**Criteria (any one triggers over time):**
1. Customer simultaneously receives and consumes benefits as entity performs
2. Entity's performance creates/enhances an asset customer controls
3. Entity's performance creates asset with no alternative use + enforceable right to payment for performance to date

**For SaaS Contracts:**
- **SaaS Platform Access**: Criterion #1 - customer consumes access continuously
- **Support Services**: Criterion #1 - customer consumes support as provided
- **Implementation (if integrated)**: Criterion #3 - may have no alternative use

**Measuring Progress:**

Select method that best depicts transfer of control:
- **Time-based (most common for SaaS)**:
  - Straight-line over subscription period
  - Example: $120,000 annual subscription = $10,000/month
  
- **Output methods**:
  - Units produced/delivered
  - Milestones reached
  - Use when outputs can be reliably measured

- **Input methods**:
  - Costs incurred (cost-to-cost)
  - Labor hours expended
  - Time elapsed
  - Use when inputs correlate with transfer of control

#### B. Point in Time Recognition

**If not over time, recognize at point when customer obtains control**

**Indicators of Transfer of Control:**
1. Entity has present right to payment
2. Customer has legal title
3. Entity has transferred physical possession
4. Customer has significant risks/rewards of ownership
5. Customer has accepted the asset

**For SaaS Contracts:**
- **Implementation Services**: Upon customer acceptance/go-live
- **Training**: Upon completion of training sessions
- **Data Migration**: Upon completion and customer acceptance

**Documentation Requirements:**
- Customer acceptance emails/sign-offs
- Go-live dates
- Completion certificates

**Revenue Recognition Schedule Example:**

```
Contract: $132,000 (SaaS $108,900 + Implementation $23,100)
Term: Jan 1, 2025 - Dec 31, 2025

Month          SaaS Revenue    Implementation    Total Revenue    Deferred Revenue
-----------    ------------    --------------    -------------    ----------------
Jan 2025       $9,075          $23,100          $32,175          $99,825
Feb 2025       $9,075          $0               $9,075           $90,750
Mar 2025       $9,075          $0               $9,075           $81,675
...
Dec 2025       $9,075          $0               $9,075           $0
-----------    ------------    --------------    -------------    ----------------
Total          $108,900        $23,100          $132,000         
```

**Contract Liabilities (Deferred Revenue):**
- Cash received but revenue not yet recognized
- Record when payment received before performance
- Reduce as revenue recognized

**Contract Assets:**
- Revenue recognized but not yet billed
- Occurs when performance precedes billing right
- Less common in SaaS (usually bill upfront)

**Key Dates:**
- **Contract Inception**: When contract terms established
- **Performance Date**: When obligation satisfied
- **Billing Date**: When invoice issued
- **Payment Date**: When cash received

**Output:** 
- Detailed revenue recognition schedule by period
- Deferred revenue rollforward
- Journal entry templates
- Key assumptions and judgments documented

---

## SaaS-Specific Considerations

### Common SaaS Business Models

1. **Pure Subscription**
   - Monthly or annual recurring fees
   - Typically one performance obligation (platform access)
   - Recognize ratably over subscription period

2. **Subscription + Implementation**
   - Upfront implementation fee + ongoing subscription
   - Two performance obligations
   - Implementation: point in time; Subscription: over time

3. **Tiered/Usage-Based**
   - Base fee + overage charges
   - Variable consideration estimation required
   - May need to constrain estimates

4. **Freemium to Paid**
   - Free trial period then paid
   - Revenue recognition starts when paid period begins
   - Trial period: no revenue (no contract exists)

### Typical SaaS Journal Entries

**Contract Signing (Cash Received Upfront):**
```
Dr. Cash                           $132,000
    Cr. Deferred Revenue                      $132,000
```

**Monthly Revenue Recognition:**
```
Dr. Deferred Revenue              $11,000
    Cr. Revenue - SaaS                        $9,075
    Cr. Revenue - Services                    $1,925
```

**Implementation Complete (if recognized separately):**
```
Dr. Deferred Revenue              $23,100
    Cr. Revenue - Implementation              $23,100
```

### Renewal Considerations

**Option to Renew:**
- Not a performance obligation until customer exercises option
- Assess if renewal option provides "material right"
- Material right = discount/benefit customer wouldn't receive without contract

**Auto-Renewal:**
- Recognize as new contract when renewal period begins
- Reassess transaction price, obligations, SSP at renewal

### Contract Modifications

**Types:**
1. **Separate Contract**: Adds distinct goods at SSP → Account as new contract
2. **Termination + New Contract**: Remaining goods distinct → Terminate old, start new
3. **Cumulative Catch-up**: Remaining goods not distinct → Adjust current contract

**Common SaaS Modifications:**
- Seat/user count changes
- Feature/module additions
- Mid-term pricing changes
- Early termination

---

## Documentation & Audit Readiness

### Required Documentation

1. **Contract Analysis Memo**
   - Performance obligations identified
   - Distinctness analysis
   - SSP determination
   - Allocation methodology
   - Recognition pattern rationale

2. **SSP Support**
   - Observable standalone sales data
   - Market research for comparable items
   - Cost buildups for cost-plus method
   - Approval from management

3. **Variable Consideration**
   - Estimation method and assumptions
   - Constraint assessment
   - Historical data supporting estimates
   - Quarterly re-assessment

4. **Customer Acceptance**
   - Go-live confirmations
   - Acceptance sign-offs
   - Email confirmations
   - System access logs

### Common Audit Questions

1. How did you determine performance obligations are distinct?
2. What is the basis for SSP when not observable?
3. How did you estimate variable consideration?
4. Why did you conclude constraint does/doesn't apply?
5. What evidence supports point-in-time recognition?
6. How do you track progress for over-time recognition?

### Internal Controls

- **Authorization**: Contracts approved before signing
- **Completeness**: All contracts captured in revenue system
- **Accuracy**: Revenue calculations independently reviewed
- **Occurrence**: Revenue recognized only for valid contracts
- **Cutoff**: Revenue recognized in correct period
- **Classification**: Revenue properly categorized by type

---

## Common SaaS Scenarios & Solutions

### Scenario 1: Simple Annual SaaS Contract
**Contract:** $12,000/year, paid upfront, 12-month term
- **Performance Obligations:** 1 (SaaS access)
- **Transaction Price:** $12,000
- **Allocation:** All to SaaS
- **Recognition:** $1,000/month over 12 months

### Scenario 2: SaaS + Implementation
**Contract:** $50,000 SaaS + $10,000 implementation
- **Performance Obligations:** 2 (SaaS and Implementation)
- **SSP:** SaaS $52,000, Implementation $12,000 (total $64,000)
- **Allocation:** SaaS $48,750, Implementation $11,250 (4.7% discount allocated proportionally)
- **Recognition:** 
  - Implementation: $11,250 at go-live
  - SaaS: $4,062.50/month over 12 months

### Scenario 3: Usage-Based Pricing
**Contract:** $2,000 base + $5 per user over 100 users
- **Performance Obligations:** 1 (SaaS access)
- **Transaction Price:** $2,000 + estimated $3,000 variable (constrained to $2,400)
- **Total:** $4,400
- **Recognition:** $366.67/month, reassess variable consideration quarterly

### Scenario 4: Multi-Year Deal with Annual Billing
**Contract:** 3 years, $100K/year, billed annually
- **Performance Obligations:** 1 per year (or 1 for full 3 years)
- **Transaction Price:** Year 1: $100K (don't include future years until billed/committed)
- **Recognition:** $8,333/month for Year 1
- **Note:** Each annual period may be treated as separate contract or renewal

### Scenario 5: Free Trial Then Paid
**Trial:** 30 days free
**Paid:** $1,200/year after trial
- **During Trial:** No contract exists (customer hasn't committed), no revenue
- **After Trial:** Contract begins, recognize $100/month
- **Note:** Trial costs are sales/marketing expense

---

## Key Takeaways for SaaS

1. **Most SaaS subscriptions = over time** (customer consumes continuously)
2. **Implementation typically = point in time** (upon acceptance)
3. **Always document SSP determination** (critical for audit)
4. **Constrain variable consideration** when uncertain
5. **Reassess estimates quarterly** (usage fees, renewals)
6. **Track acceptance evidence** (emails, confirmations)
7. **Multi-year deals**: Recognize year-by-year unless full commitment
8. **Renewals**: Generally new contract, reassess terms
9. **Modifications**: Determine if separate contract or adjustment
10. **Deferred revenue**: Balance sheet liability, not "backlog"

---

## References & Resources

- **FASB ASC 606**: Revenue from Contracts with Customers
- **Deloitte Roadmap**: Revenue Recognition Guide
- **PwC Revenue Guide**: Comprehensive revenue recognition guidance
- **EY Technical Line**: Revenue recognition publications
- **AICPA**: Revenue Recognition Audit Guide

---

*This guide provides general guidance. Complex arrangements may require consultation with accounting professionals and auditors.*
