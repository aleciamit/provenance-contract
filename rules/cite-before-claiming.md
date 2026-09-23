# Cite before claiming

The pre-edit hook fires only when a file is edited. It catches nothing on the day an agent
confidently describes a piece of existing UI wrong, in conversation, with no file being touched.
This rule closes that gap.

**No color, label, size, state or behavior of the product is stated as fact unless it has just
been read and can be pointed to by file and line.** Where it cannot be cited, the answer is
"let me check", followed by checking.

This applies to:

- describing what a screen currently shows;
- saying what a class, token or component does;
- reporting whether something is implemented, wired or reachable;
- counting anything. Read the source; never do arithmetic on a screenshot.

The shape of a compliant sentence: "`index.html:412` sets the chip background to `--accent-soft`."
The shape of a violation: "the chips use the soft accent, I believe." The second one costs the
owner a read, an evaluation and a correction, and it is wrong often enough that the first one is
always the smaller cost.

Keep this file in the project, or in the agent's memory directory so it carries from one project
to the next.
