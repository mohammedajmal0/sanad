# Success metrics

The JD lists eight success measures, and Sanad reports a number for each. In the interview, "how would you measure success?" gets answered with a dashboard rather than an opinion. All eight go on one AI/BI dashboard in Phase 7, fed by MLflow traces, evaluation runs and gateway usage tables.

| JD success measure | Sanad metric | Source | Target | Latest |
|---|---|---|---|---|
| Agents delivered to production and their impact | Agents live; tasks completed per week | Deployments, `task_completed` scorer | TODO(human) | |
| Adoption, satisfaction, task completion | Active users, conversations per user, thumbs-up rate, completion rate | Chat UI feedback, traces | TODO(human) | |
| Accuracy, groundedness, reliability, safety | Correctness, groundedness and safety pass rates; error rate | MLflow judges on evaluation runs and sampled production traces | TODO(human) | |
| Less manual effort and faster cycle time | Minutes per task with and without the agent, for three scripted tasks | Timed runs you record, labelled as simulated | TODO(human) | |
| Reusable, maintainable delivery | Days to scaffold a new agent from the template; test coverage | Phase 8 template, CI report | TODO(human) | |
| Security, privacy, governance compliance | PII leaks in red-team set; writes executed without approval | Custom scorers, audit tables | 0 and 0 | |
| Reliability, latency, scale, cost | p95 latency; cost per conversation; behaviour under a small load test | Traces, gateway usage tracking | TODO(human) | |
| Partnerships across teams | Expert feedback collected on traces | MLflow labeling sessions | TODO(human) | |

Targets are set in Phases 6 and 7, with a one-line justification for each.

## Two honesty rules

- Label simulated business numbers as simulated.
- Show at least one metric that got worse before it got better, and what you changed. Interviewers trust a real iteration story more than a perfect score.
