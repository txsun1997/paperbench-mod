Manages the task execution plan with read, edit, or write operations. The plan content is a Markdown document that records the plan and current progress for the task. 

Usage:
- `read`: Returns the current plan. No other parameters needed.
- `edit`: Replaces a unique `old_string` with `new_string` in the plan.
- `write`: Replaces the entire plan with `new_plan`.

Rules:
- For `edit`: Both `old_string` and `new_string` are required. The `old_string` must appear exactly once in the plan.
- For `write`: The `new_plan` is required and cannot be empty.
- MUST read the plan periodically to check that you are on track with the plan.
- You can update the plan in the following situations:
  1. You have made significant progress on the task and need to update the plan to reflect the progress.
  2. You have encountered a problem and current plan is not working. You need to re-plan the task and update the plan with suitable solutions to solve the problem.
  3. If your context is compacted, you need to read the plan to understand the current progress before continuing the task.

- IMPORTANT: When calling **PhaseController** tool to exit the planning phase, the "plan" will be updated automatically. You DO NOT need to call this tool to update the plan.
