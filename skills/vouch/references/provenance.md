# Provenance policy

Each metric in the corpus carries a tag saying how sure the user is. The tag —
not the drafting model's judgement — decides how a fact may appear. The same
table is encoded in `scripts/vouch_common.py` (`SURFACE`, `GROUNDING`).

| Tag | Meaning | When drafting | After verification (supported) |
|---|---|---|---|
| `verifiable` | proof exists, or the user can defend it in an interview | use as is, exact numbers included | keep |
| `estimate` | from memory, approximate | may appear, **never as a precise figure** ("roughly", "dozens", or no number) | soften |
| `from-cv` | copied from an old CV, not yet confirmed | use cautiously; flag it to the user if a line rests on it | flag |
| `cannot-confirm` | checked, and the user could not confirm it | **the number never appears**; the record's prose may | flag |

Provenance tags *figures*, so verification reads it off the figures a line
repeats: a line quoting a verifiable metric stays verifiable even if the same
record also holds an estimate; a line with no figure has nothing to soften; a
figure that matches no metric takes the record's **most cautious** tag
(verifiable < estimate < from-cv < cannot-confirm). A fact can only get more
cautious on its way to the page, never less.

Unsupported claims → **remove_or_verify**: delete the line, or — if it is true —
add the fact to the corpus with an honest tag and re-run.

A claim the judge did not answer, or answered unreadably, is **unverified**: no
verdict is not a "no". It is shown for the user to check by eye.

Promoting a tag (estimate → verifiable) is the user's call, made with evidence.
Never promote a tag on the user's behalf, and never demote `cannot-confirm`.
