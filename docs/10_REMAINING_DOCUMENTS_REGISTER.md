# Remaining Documents Register

The current pack is sufficient to start implementation. Create the following documents only when their trigger occurs.

| Document | Create when | Owner | Why it is deferred |
|---|---|---|---|
| Database migration guide | First real migration is added | Backend owner | Must reflect actual migration tool and schema |
| Seed-data catalogue | Generator fixtures stabilize | Data owner | Early fixture values will change |
| API change log | First breaking contract change | Backend owner | No released contract exists yet |
| UI component inventory | Three or more shared patterns exist | Frontend owner | Avoid documenting speculative components |
| Deployment runbook | A hosting target is selected | Backend/DevOps | Local Docker is the current baseline |
| Incident/recovery runbook | Persistent shared demo environment exists | Team lead | No operational environment exists yet |
| Privacy impact assessment | Real or partner data is proposed | Product/security | Synthetic-only MVP has no real PII |
| Threat model | Authentication or external integration begins | Security reviewer | Current local prototype has limited exposure |
| Release notes | First demo release is tagged | Team lead | No release yet |
| License decision | Before making the repository public | Project owner | The owner must choose the intended license |
| User research script | Interviews are scheduled | Product owner | Implementation is the immediate task |

Do not create these as empty templates merely to increase documentation volume. Add them when the project contains the real decisions they need to preserve.
