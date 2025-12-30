

<system-reminder>
The TodoWrite tool can help you better manage tasks when configuring environment. You can use the TodoWrite tool to manage the todo items you need to conduct during the environment setup, but please do not list items unrelated to environment setup. 

The todo items related to environment setup maybe like "Verifying GPU availability and driver compatibility", "Installing or verifying Conda/Miniforge installation", "Creating new conda environment with specific Python version", "Installing dependencies from requirements.txt", "Validating GPU accessibility from Python", etc.

Todo items unrelated to environment setup maybe like "Implementing training code", "Evaluating model performance", "Installing dependencies", "Running training scripts", "Monitoring training process", "Downloading dataset from official source", "Transforming data format to required structure", etc.

The current content of the todo list is

{todo}, 

and there may already be items related to environment setup in this todo list: 
- IMPORTANT: When you need to add new items, please add them after the existing environment setup items instead of only adding them at the end of the entire todo list;
- IMPORTANT: When you need to modify certain environment setup items, please directly edit the existing environment setup items;
- IMPORTANT: It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.

IMPORTANT: You MUST call the **PhaseController** tool to exit "environment setup" phase when you need to switch to another phase. 
IMPORTANT: When you use the PhaseController tool to exit the "environment setup" phase, the "new_phase" parameter is required, while the "plan" parameter is prohibited. If the task flow of the "environment setup" phase is relatively complex, you need to generate a "summary" parameter to help the user clearly understand what you have done during this phase.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>