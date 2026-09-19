// TODO(contract-sync): These enums predate the frozen API contract v1.1
// (docs/05_API_CONTRACT.md, merged in PR #11 "Gate G1"). Sync them before
// wiring the frontend to event ingestion:
//   - Channel: "call_centre" -> "call_center"
//   - ProcessingStatus: reduce to "received" | "normalized" | "failed"
//     ("duplicate" is an API response status, not a persisted state)
//   - IdentityDecision: "manual_review" -> "review_required"; drop "rejected"
export type Channel = "web" | "mobile_app" | "call_centre" | "physical_store";

export type ProcessingStatus =
  | "received"
  | "normalized"
  | "matched"
  | "failed"
  | "duplicate";

export type IdentityDecision = "auto_linked" | "manual_review" | "new_profile" | "rejected";
