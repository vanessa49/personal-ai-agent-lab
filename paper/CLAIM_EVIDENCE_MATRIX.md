# Paper 1 Claim–Evidence Matrix

Canonical manuscript: `paper/main_updating_CHI.md`  
Public evidence root: `cognitive-trajectory/evidence/paper1/`

| Claim family | Manuscript location | Authoritative artifact | Exact source |
|---|---|---|---|
| Corpus size and integrity | Abstract; Study Overview; Dataset | `pipeline_validation_dedup_1122.json` | `.raw`, `.personalGraphs`, `.checks` |
| Structural collapse | Key Findings; Table 1; Structural Analysis | `table1_dedup_1122.json` | `.results[].stats` |
| Random QA divergence | Key Findings; Table 2; Trajectory Dynamics | `pseudo_trajectory_dedup_1122.json` | `.metrics.ksInternal` |
| Semantic reconstruction | Key Findings; Trajectory Dynamics | `pseudo_trajectory_dedup_1122.json` | `.metrics.ksSemantic` |
| Order dependence | Key Findings; Trajectory Dynamics; Limitations | `pseudo_trajectory_dedup_1122.json` | `.metrics.ksShuffled` |
| External QA comparison | Table 2 | `pseudo_trajectory_dedup_1122.json` | `.metrics.ksExternal` |
| Topic-drift control | Controls | `pseudo_trajectory_dedup_1122.json` | `.metrics.topicDrift` |
| Wasserstein and KL robustness | Controls | `pseudo_trajectory_dedup_1122.json` | `.metrics.wassersteinDistance`, `.metrics.klDivergence` |
| First-order QA continuity | Trajectory Dynamics | `qa_gap_current.json` | `.results[].stats.avgSimilarity`, `.avgGap` |
| Privacy-safe compact record | Supplement / repository | `paper1_results_summary.json` | generated aggregate plus SHA-256 provenance |

## Paper-facing rounded values

| Metric | Value |
|---|---:|
| Sessions / role-marked turns | 1,122 / 35,756 |
| Cognitive nodes / edges | 13,312 / 12,230 |
| Cognitive mean / max chain | 2.15 / 13 |
| Cognitive long-chain ratio | 8.6% |
| QA sampled mean / max chain | 1.12 / 2 |
| QA full mean / max chain | 1.11 / 2 |
| KS random QA / semantic / fully random | 0.298 / 0.087 / 0.168 |
| KS SQuAD / shuffled real | 0.307 / 0.101 |
| Wasserstein / KL | 0.188 / 1.074 |
| QA full similarity / gap | 0.731 / 0.269 |
| QA sampled similarity / gap | 0.723 / 0.277 |

## Excluded evidence

- Pre-deduplication 3,048-graph results under `cognitive-trajectory/experiment_results/`
- The obsolete 29.5% content-overlap claim
- Length-control output from the unfinished historical run
- Leaked QA pilot and 549-item behavioral results
- Repaired 441-item fine-tuning/RAG evaluation, relation-hit metrics, and interaction-policy distance

The final group belongs to Paper 2. Its exclusion is a scope boundary, not missing Paper 1 evidence.
