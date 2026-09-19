export type Channel = "web" | "mobile_app" | "call_centre" | "physical_store";

export type ProcessingStatus =
  | "received"
  | "normalized"
  | "matched"
  | "failed"
  | "duplicate";

export type IdentityDecision = "auto_linked" | "manual_review" | "new_profile" | "rejected";
