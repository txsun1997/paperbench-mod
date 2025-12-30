
<system-reminder>
When monitoring training status, there is only one todo item:
- Monitor training logs and computing resource utilization

You can use the TodoWrite tool to manage these todo items, but please do not list items unrelated to training status monitoring. The current content of the todo list is

{todo}, 

and there may already be items related to training status monitoring in this todo list: 
- IMPORTANT: When you need to add new items, please add them after the existing training status monitoring items instead of only adding them at the end of the entire todo list;
- IMPORTANT: When you need to modify certain training status monitoring items, please directly edit the existing training status monitoring items;
- IMPORTANT: It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.

# Important Reminders
- Do not stop monitoring and mark the todo items related to monitoring as completed after running the bashoutput tool or checking log files a few times. Only mark the todo items related to monitoring as completed when the training is running stably and machine utilization is balanced and sufficient unless the training status is abnormal.
- If any abnormalities occur during training, after stopping the training, the monitoring report and marking the todo items related to monitoring as completed using the todowrite tool must be output in the same message.
- IMPORTANT: It is critical that you mark the todo as completed as soon as you are done with the task.

IMPORTANT: You MUST call the **PhaseController** tool to exit "training monitor" phase when you need to switch to another phase. 
IMPORTANT: When you use the PhaseController tool to exit the "training monitor" phase, the "new_phase" parameter is required, while the "plan" parameter is prohibited. If the task flow of the "training monitor" phase is relatively complex, you need to generate a "summary" parameter to help the user clearly understand what you have done during this phase.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>