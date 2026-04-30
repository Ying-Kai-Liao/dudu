## REMOVED Requirements

### Requirement: Market-context replaces market-problem

**Reason**: The deprecation wrapper at `skills/market-problem/` was introduced in `split-background-and-pmf-layers` to give users one release window of overlap between the old name (`dudu:market-problem`) and the new name (`dudu:market-context`). That window has closed. The wrapper is being deleted, and with it the requirement that the wrapper exists, prints a deprecation notice, or forwards invocations.

**Migration**: Users invoking `dudu:market-problem` after this change lands will receive a "skill not found" error. They must invoke `dudu:market-context` directly. The migration was already advertised by the deprecation notice the wrapper printed during its release window. Any out-of-tree automation referring to the old name must be updated; in-tree references are scrubbed by the tasks artifact of this change.

The two surviving requirements from the foundation spec — "Market-context produces public-source context only" and "Existing personas under deals/<slug>/personas/ are preserved on disk" — are unchanged and remain in force.
