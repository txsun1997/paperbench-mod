Read the conversation above, which represents a completed phase of the agent's work session. Your goal is to create a concise yet comprehensive summary that captures:

1. **Phase Overview**: What was the main objective of this phase, what has been done so far?
2. **Key Actions**: What major actions were taken during this phase, what the major decisions were made and why?
3. **Results & Outcomes**: What were the results, decisions, or artifacts produced, and how to use them to continue the work?
4. **Important Context**: Any crucial information that should be remembered for future phases, the issues you have encountered and how you have resolved them.
5. **Unresolved Items**: Any pending issues or tasks that need attention, what is the next step you will take?

## Compression Guidelines

- Be CONCISE but COMPLETE - capture all important information
- Focus on OUTCOMES and RESULTS rather than detailed process steps
- Highlight DECISIONS made and their rationales
- Note any ERRORS or ISSUES encountered and how they were resolved
- Preserve SPECIFIC details like file names, commands, configurations, error messages
- Remove redundant tool calls and verbose outputs unless they contain critical information

**IMPORTANT**: If the phase is `plan`, you should keep ALL the original details of the resulting plan in the summary.

## Output Format

Provide your summary in the following format:

```xml
<phase_summary>
## Phase: [Phase Name]

## Objective
[Main objective of this phase]

## Actions
[Key actions taken, bullet points]

## Results
[Outcomes and artifacts produced]

## Context
[Important context for future reference]

## Unresolved
[Any pending items or issues]
</phase_summary>
```

Remember: This summary will replace the detailed conversation history. Keep important details for future reference.

