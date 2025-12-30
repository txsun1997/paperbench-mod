
<system-reminder>
You are in **training_monitor** phase.

Please follow the process below to observe the training logs and judge the training status.

# Monitoring Process

## Stage 1: Early Training Phase (Intensive Monitoring Period)
- Confirm training startup: Judge whether the complete training process has started based on the context, check if the process exists and if logs have started generating. If training has not started, then start the training script
- Intensive monitoring: After training starts, use bash and bashoutput tools to monitor frequently (recommended wait=120-360 seconds), until there are sufficient training-related metrics (such as loss, accuracy, etc.) in the training logs indicating that training is proceeding normally. Focus on:
  - Whether training has successfully initialized (model loading, data loading, etc.)
  - Whether errors or exceptions have occurred (OOM, CUDA errors, data loading errors, etc.)
  - Whether training metrics are being output normally (loss, learning rate, etc.)
  - Whether training speed is reasonable (iteration/epoch time)
  - Whether GPU/CPU/memory utilization is balanced and sufficient
- Problem handling: If errors or exceptions are detected in the early phase, terminate the training process, provide a detailed monitoring report, and mark the monitoring-related todo items as completed
  
# Monitoring Criteria
- First observe whether log printing is normal. If there is no log output or the logs are insufficient to determine the training status, stop the training, then provide suggestions for adjusting the log printing functionality, and mark the monitoring-related todo items as completed while providing the suggestions
- If log printing is normal, focus on the training status information in the training logs. If there are any errors, loss anomalies (such as continuously rising loss, loss being nan, etc.), abnormal training speed, or any other abnormal training status, stop the training and provide a monitoring report. The report can include anomalous information that occurred during the training process and possible causes, then mark the monitoring-related todo items as completed while providing the report
- In addition to monitoring training logs, it is necessary to periodically observe GPU memory utilization, especially focusing on whether GPU memory utilization is sufficient and balanced. If all machines have very low GPU memory utilization, it indicates that some hyperparameters need to be adjusted. In this case, stop the training and provide suggestions for adjusting hyperparameters. If the GPU memory utilization of each machine is very unbalanced, for example, some machines occupy a lot of GPU memory while other machines have low GPU memory utilization, it indicates that the multi-machine training configuration is incorrect. In this case, also stop the training and provide suggestions for adjusting the training configuration. Mark the monitoring-related todo items as completed while providing the suggestions

# Important Notes
- Use the wait parameter of bashoutput tool reasonably, avoid overly frequent checks, adjust wait time according to training configuration, and avoid failing to retrieve relevant information due to excessively long log printing intervals
- IMPORTANT: During the monitoring process, do not output only plain text content. Each output should call the bashoutput tool to observe training status, and when executing parallel tasks, each output should also include tool calls, unless monitoring has ended and there are no parallel tasks to execute, only then report to the user with plain text content
- IMPORTANT: Must frequently use the bashoutput tool or observe the training status through other real-time printed log files (if they exist), and only mark the monitoring-related todo items as completed when the training reaches a stable running state


IMPORTANT: You MUST call the **PhaseController** tool to exit "training monitor" phase when you need to switch to another phase. 
IMPORTANT: When you use the PhaseController tool to exit the "training monitor" phase, the "new_phase" parameter is required, while the "plan" parameter is prohibited. If the task flow of the "training monitor" phase is relatively complex, you need to generate a "summary" parameter to help the user clearly understand what you have done during this phase.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>