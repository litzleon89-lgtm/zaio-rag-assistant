# Assistant Test Cases

Run the automated suite with `pytest -q`. These live cases were checked against the current ZAIO crawl and the supplied 26-page Student Handbook PDF.

| Question | Retrieved source | Generated answer |
|---|---|---|
| What courses does ZAIO offer? | `https://www.zaio.io/compare-courses` | Fullstack AI Engineer, Cloud & DevOps Engineering, Fullstack Web Development, Data Science, Cybersecurity, and Digital Marketing. The generated response also includes retrieved duration, pricing, technologies, career paths, and certification details. |
| What are the recommended minimum laptop hardware requirements? | `Student Handbook - Page 5` | A current Windows laptop with PowerShell or a Mac with Terminal; recommended internet speeds are 10 Mbps download and 3 Mbps upload. |
| What does the handbook say about communication channels? | `Student Handbook - Page 18` | Communication is via email before Orientation Day and transitions to Discord after the bootcamp begins. |
| How does ZAIO communicate before classes start? | `Student Handbook - Page 18` | Communication is via email before Orientation Day; the answer is retrieved from the handbook despite the question's paraphrasing. |
| What was ZAIO's revenue last year? | None | `I could not find that information in the available knowledge base.` |

## Unit Test Results

The suite verifies chunk overlap, handbook HTML fallback extraction, PDF letter-spacing normalization, removal of website chrome, crawler scope, vector ranking, source attribution, course-catalog ranking, source-specific retrieval, handbook topic retrieval, paraphrased communication routing, and refusal behavior.

Verified locally on 2026-09-28 with Python 3.14.7: `17 passed` (60 dependency deprecation warnings). The live index contains 68 chunks: 26 page-numbered handbook chunks and 42 ZAIO website chunks.