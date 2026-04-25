# 07 - Evaluation Strategy

## Evaluation Objective

TraceVault must be evaluated as an enterprise knowledge reasoning system, not only as a chatbot.

The evaluation must measure:

- retrieval quality
- grounding quality
- citation accuracy
- hallucination risk
- reasoning usefulness
- governance compliance

## Evaluation Dataset

Create a test set with 30-50 questions across multiple document types.

Recommended question categories:

| Category | Example |
|---|---|
| Fact lookup | What project used Veeam backup? |
| Exact match | Which document mentions AZ-305? |
| Synthesis | What are the main strategic gaps? |
| Pattern detection | What failure patterns appear repeatedly? |
| Temporal analysis | How did the architecture direction evolve? |
| Scenario planning | What should we do if vector search fails? |
| Conflict detection | Which notes contradict each other? |
| Evidence challenge | Which source supports this answer? |

## Key Metrics

### Retrieval Metrics

| Metric | Meaning |
|---|---|
| Recall@K | Did the correct chunk appear in top K? |
| Precision@K | How many retrieved chunks were relevant? |
| MRR | How high was the first relevant result? |
| Hybrid gain | Did vector + keyword outperform vector only? |

### Answer Metrics

| Metric | Meaning |
|---|---|
| Groundedness | Claims are supported by retrieved evidence |
| Citation accuracy | Citations actually support the answer |
| Completeness | Answer covers the user's question |
| Faithfulness | Answer does not distort source meaning |
| Usefulness | Answer helps decision-making |

### Governance Metrics

| Metric | Meaning |
|---|---|
| Source traceability | Every claim links to chunk/source |
| Unsupported claim rate | Lower is better |
| Raw/cleaned conflict detection | Conflicts are flagged |
| Sensitive data handling | Restricted content is controlled |

## Evaluation Scorecard

```text
Retrieval Quality:      /10
Citation Accuracy:      /10
Groundedness:           /10
Reasoning Usefulness:   /10
Governance Compliance:  /10
Security Awareness:     /10
Overall Enterprise Fit: /10
```

## Test Case Template

```yaml
id: EVAL-001
question: "What is the strongest career positioning direction?"
expected_evidence:
  - document_id: "project_ascend_300"
  - chunk_id: "..."
expected_answer_points:
  - "Hybrid Cloud & AI Platform Architecture"
  - "Avoid generic AI engineer reset"
  - "Leverage enterprise infrastructure background"
evaluation_notes:
  - "Must cite supporting source chunks"
```

## Pass Criteria for MVP

The MVP should achieve:

- correct evidence in top 5 for at least 80% of test questions
- citation accuracy above 85%
- unsupported claim rate below 10%
- clear confidence/gap reporting in every strategic answer

## Why Evaluation Matters

For a portfolio project, evaluation proves maturity. It shows that the system is not merely generating impressive text, but producing measured, evidence-based outcomes.
