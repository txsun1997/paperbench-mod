<system-reminder>
You are in **data processing** phase. The task requires to process or synthesize data. Please complete data collection, generation or processing according to the task content and the user requirements.

**IMPORTANT**: You should read the `ml-data-processing` skill for detailed best practices on data collection, processing, synthetic data generation, and validation. If applicable, you should follow the workflows and expert advices there.

IMPORTANT: You MUST call the **PhaseController** tool to exit "data processing" phase when you need to switch to another phase. 
IMPORTANT: When you use the PhaseController tool to exit the "data processing" phase, the "new_phase" parameter is required, while the "plan" parameter is prohibited. If the task flow of the "data processing" phase is relatively complex, you need to generate a "summary" parameter to help the user clearly understand what you have done during this phase.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>