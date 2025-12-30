

<system-reminder>
The TodoWrite tool can help you better manage tasks when evaluating the trained model. You can use the TodoWrite tool to manage the todo items you need to conduct during evaluating the trained model, but please do not list items unrelated to evaluation. 

The todo items related to evaluation maybe like "Creating evaluation results table with benchmarks and metrics", "Researching standard evaluation protocols for target benchmarks", "Collecting baseline results from published papers", "Implementing evaluation scripts using official libraries", "Running evaluation on test datasets", "Filling in evaluation results table", etc.

Todo items unrelated to evaluation maybe like, "Testing training pipeline on small dataset", "Implementing distributed training configuration", "Implementing training code", "Installing dependencies", "Running training scripts", "Monitoring training process", "Downloading dataset from official source", "Transforming data format to required structure", "Analyzing training loss convergence trends", "Comparing performance metrics with baselines", etc.

The current content of the todo list is

{todo}, 

and there may already be items related to evaluation in this todo list: 
- IMPORTANT: When you need to add new items, please add them after the existing evaluation items instead of only adding them at the end of the entire todo list;
- IMPORTANT: When you need to modify certain evaluation items, please directly edit the existing evaluation items;
- IMPORTANT: It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.

IMPORTANT: You MUST call the **PhaseController** tool to exit "evaluation" phase when you need to switch to another phase. 
IMPORTANT: When you use the PhaseController tool to exit the "evaluation" phase, the "new_phase" parameter is required, while the "plan" parameter is prohibited. If the task flow of the "evaluation" phase is relatively complex, you need to generate a "summary" parameter to help the user clearly understand what you have done during this phase.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>