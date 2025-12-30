

<system-reminder>
The TodoWrite tool can help you better manage tasks when analyzing the training results. You can use the TodoWrite tool to manage the todo items you need to conduct during analyzing the training results, but please do not list items unrelated to result analysis. 

The todo items related to result analysis maybe like "Analyzing training loss convergence trends", "Comparing performance metrics with baselines", "Investigating error cases and failure patterns", "Diagnosing overfitting or underfitting issues", "Extracting key findings from validation results", etc.

Todo items unrelated to result analysis may like "Configuring the training environment", "Implementing training code", "Evaluating model performance", "Preparing and preprocessing datasets", "Installing dependencies", "Running training scripts", "Monitoring training process", etc.

The current content of the todo list is

{todo}, 

and there may already be items related to result analysis in this todo list: 
- IMPORTANT: When you need to add new items, please add them after the existing analysis items instead of only adding them at the end of the entire todo list;
- IMPORTANT: When you need to modify certain analysis items, please directly edit the existing analysis items;
- IMPORTANT: It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.

IMPORTANT: You MUST call the **PhaseController** tool to exit "analysis" phase when you need to switch to another phase. 
IMPORTANT: When you use the PhaseController tool to exit the "analysis" phase, the "new_phase" parameter is required, while the "plan" parameter is prohibited. If the task flow of the "analysis" phase is relatively complex, you need to generate a "summary" parameter to help the user clearly understand what you have done during this phase.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>