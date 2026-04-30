## REMOVED Requirements

### Requirement: customer-discovery skill becomes a deprecation stub

**Reason**: The deprecation stub at `skills/customer-discovery/` was introduced in `split-background-and-pmf-layers` to give users one release window of overlap between the old name (`dudu:customer-discovery prep` / `dudu:customer-discovery debrief`) and the new layered surface (`dudu:pmf-signal` for prep-as-side-effect, `dudu:customer-debrief` for the synthesis step). That window has closed. The stub is being deleted, and with it the requirement that it exists, prints a migration message, or forwards `prep`/`debrief` invocations to their new homes.

**Migration**: Users invoking `dudu:customer-discovery debrief` after this change lands receive a "skill not found" error and must invoke `dudu:customer-debrief` directly. Users invoking `dudu:customer-discovery prep` similarly receive "skill not found" and must invoke `dudu:pmf-signal` (which produces `customer-discovery-prep.md` as a Stage 5 side effect, per the surviving "PMF-signal continues to emit the legacy-shape customer-discovery-prep" requirement). Both migration paths were advertised by the stub during its release window.

The two surviving requirements from the foundation spec — "Customer-debrief is a standalone skill" and "Customer-debrief has no orchestrator coupling" — are unchanged and remain in force.
