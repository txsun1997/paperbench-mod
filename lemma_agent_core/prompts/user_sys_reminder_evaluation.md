
<system-reminder>
You are in **evaluation** phase. Please use search tools to confirm the usage methods of evaluation benchmarks and correctly evaluate the results of the trained model on each benchmark.

You must follow the steps below to complete evaluation tasks:
1. **Create an empty table, which should follow professional academic style, before performing any concrete evaluation work**: Do neccessary research to carefully determine the key factors for evaluation, including benchmarks (specific datasets and experimental settings), metrics, baselines, and target methods or models to be tested. Keep in mind the table you plan to fill in during the entire evaluation process.
2. **Fill in the numbers that are already known in the table**: Some numbers in the table can be easily accessed before heavy coding work, for example, dataset statistics can be retrieved from the data processing logs, and experimental results of some baselines on specific benchmarks can be found in published papers. You should carefully fill in the table and double check these known numbers.
3. **Implement evaluation code**: The evaluation code should be very precise. In many cases, you can find official or standard implementation of the evaluation method in high-quality repositories or using popular libraries. You should try your best to ensure a fair comparison, otherwise you should point out the differences in the evaluation methods.
4. **Run the evaluation scripts and fill in the table**: Finally, you should run your evaluation scripts and carefully fill in the table the evaluation results.

IMPORTANT: You MUST call the **PhaseController** tool to exit "evaluation" phase when you need to switch to another phase. 
IMPORTANT: When you use the PhaseController tool to exit the "evaluation" phase, the "new_phase" parameter is required, while the "plan" parameter is prohibited. If the task flow of the "evaluation" phase is relatively complex, you need to generate a "summary" parameter to help the user clearly understand what you have done during this phase.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>