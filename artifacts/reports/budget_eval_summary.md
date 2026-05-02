# Budget Evaluation Summary

Three measured local ablation levels, all at $0 spend (no paid APIs).

| Level | Description | Routing % | Op Success % | Evidence % | Avg Latency (s) | Spend |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| router_only | Route question; return tier label, no operator execution. | 92.5 | 100.0 | 0.0 | 0.0 | $0.00 |
| operator_no_evidence | Run operator; return answer text only (evidence suppressed). | 92.5 | 100.0 | 0.0 | 0.025 | $0.00 |
| operator_with_evidence | Full pipeline: operator + evidence collection (current syste | 92.5 | 100.0 | 100.0 | 0.024 | $0.00 |

## Notes

- All three levels run deterministically with no external API calls.
- Evidence coverage improvement from Level 0 → Level 2 demonstrates the value of the operator pipeline.
- Paid $5 (embedding reranking) and $20 (LLM synthesis) tiers remain as planned ablations.
