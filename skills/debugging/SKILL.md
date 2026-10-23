---
name: debugging
description: Use when something works sometimes or fails without a clear error.
---

# Debugging

1. Reproduce it twice. If it is not reproducible, stop and write down what is
   different between the runs - that difference *is* the bug's address.
2. Find the first wrong value, not the last. Walk backwards from the symptom
   until the value still looks correct; the step after it is the suspect.
3. Change one thing. If you change two, you learn nothing.
4. Write the cause in the project's handoff pack under `## Gotchas` before you
   leave. A fixed bug that is not written down comes back as a new bug.
