

<system-reminder>
The TodoWrite tool can help you better manage tasks when processing data. You can use the TodoWrite tool to manage the todo items you need to conduct during the data processing, but please do not list items unrelated to data processing. 

The todo items related to data processing maybe like "Downloading dataset from official source", "Transforming data format to required structure", "Filtering and cleaning raw data", "Validating data quality and checking examples", "Splitting dataset into train/val/test sets", "Implementing data preprocessing pipeline", "Generating synthetic data using LLMs", "Applying data augmentation strategies", etc.

Todo items unrelated to result analysis may like "Configuring the training environment", "Implementing training code", "Evaluating model performance", "Installing dependencies", "Running training scripts", "Monitoring training process", etc.

The current content of the todo list is

{todo}, 

and there may already be items related to data processing in this todo list: 
- IMPORTANT: When you need to add new items, please add them after the existing data processing items instead of only adding them at the end of the entire todo list;
- IMPORTANT: When you need to modify certain data processing items, please directly edit the existing data processing items;
- IMPORTANT: It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.

IMPORTANT: You MUST call the **PhaseController** tool to exit "data processing" phase when you need to switch to another phase. 
IMPORTANT: When you use the PhaseController tool to exit the "data processing" phase, the "new_phase" parameter is required, while the "plan" parameter is prohibited. If the task flow of the "data processing" phase is relatively complex, you need to generate a "summary" parameter to help the user clearly understand what you have done during this phase.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>