# SCRUB.local.md (copy this file to SCRUB.local.md; the copy is never committed)

Terms that must never appear in a published file. The checker reads every term written in
backticks under the heading below, and refuses to report clean if it reads none.

## Never reintroduce

- `Example Employer Inc`
- `Example Employer`
- `Jane Realperson`
- `internal-tool-name`
- `ACME`

Nothing below this line is parsed as a term.

Notes on why each term is listed can go here. Short all-caps codes (three letters or fewer) are
matched case-sensitively so they do not fire inside encoded data. Multi-word terms are also
matched with every separator stripped, so `Example Employer` catches `example.employer@` and
`exampleemployer.com`.
