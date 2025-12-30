

<system-reminder>
The TodoWrite tool can help you better manage tasks when implementing training code. You can use the TodoWrite tool to manage the todo items you need to conduct during implementing the training code, but please do not list items unrelated to training code implementation. 

The todo items related to training code implementation maybe like "Researching training algorithm and loss function selection", "Understanding algorithm implementation details from official repos", "Writing training loop with forward/backward propagation", "Configuring checkpoint saving and loading mechanism", "Setting up logging and visualization tools", "Determining hyperparameters from literature search", "Testing training pipeline on small dataset", "Implementing distributed training configuration", etc.

Todo items unrelated to training code implementation maybe like "Implementing evaluation scripts", "Evaluating model performance", "Implementing data preprocessing pipeline", "Installing or verifying Conda/Miniforge installation", "Installing dependencies", "Monitoring training process", "Downloading dataset from official source", "Transforming data format to required structure", "Analyzing training loss convergence trends", etc.

The current content of the todo list is

{todo}, 

and there may already be items related to training code implementation in this todo list: 
- IMPORTANT: When you need to add new items, please add them after the existing training code implementation items instead of only adding them at the end of the entire todo list;
- IMPORTANT: When you need to modify certain training code implementation items, please directly edit the existing training code implementation items;
- IMPORTANT: It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.

IMPORTANT: You MUST call the **PhaseController** tool to exit "training code omplementation" phase when you need to switch to another phase. 
IMPORTANT: When you use the PhaseController tool to exit the "training code omplementation" phase, the "new_phase" parameter is required, while the "plan" parameter is prohibited. If the task flow of the "training code omplementation" phase is relatively complex, you need to generate a "summary" parameter to help the user clearly understand what you have done during this phase.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>