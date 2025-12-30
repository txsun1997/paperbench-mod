
<system-reminder>
Training monitor mode is active. 

Please follow the process below to observe the training logs and judge the training status.

# Monitoring Process

## Stage 1: Early Training Phase (Intensive Monitoring Period)
- Confirm training startup: Judge whether the complete training process has started based on the context, check the GPU job status with ViewGPUJob and if logs have started generating.
- Intensive monitoring: After training starts, use bash command `tail` to read the newest outputs in the logs and ViewGPUJob tool to monitor frequently (recommended wait=120-360 seconds), until there are sufficient training-related metrics (such as loss, accuracy, etc.) in the training logs indicating that training is proceeding normally. Focus on:
  - Whether training has successfully initialized (model loading, data loading, etc.)
  - Whether errors or exceptions have occurred (OOM, CUDA errors, data loading errors, etc.)
  - Whether training metrics are being output normally (loss, learning rate, etc.)
  - Whether training speed is reasonable (iteration/epoch time)
  - Whether GPU utilization is balanced and sufficient
- Problem handling: If errors or exceptions are detected in the early phase, terminate the training process, provide a detailed monitoring report, and mark the monitoring-related todo items as completed

# Monitoring Criteria
- First observe whether log printing is normal. If there is no log output or the logs are insufficient to determine the training status, stop the training, then provide suggestions for adjusting the log printing functionality, and mark the monitoring-related todo items as completed while providing the suggestions
- If log printing is normal, focus on the training status information in the training logs. If there are any errors, loss anomalies (such as continuously rising loss, loss being nan, etc.), abnormal training speed, or any other abnormal training status, stop the GUP job and provide a monitoring report. The report can include anomalous information that occurred during the training process and possible causes, then mark the monitoring-related todo items as completed while providing the report
- In addition to monitoring training logs, it is necessary to periodically observe GPU memory utilization in the log, especially focusing on whether GPU memory utilization is sufficient and balanced. If all machines have very low GPU memory utilization, it indicates that some hyperparameters need to be adjusted. In this case, stop the training and provide suggestions for adjusting hyperparameters. If the GPU memory utilization of each machine is very unbalanced, for example, some machines occupy a lot of GPU memory while other machines have low GPU memory utilization, it indicates that the multi-machine training configuration is incorrect. In this case, also stop the training and provide suggestions for adjusting the training configuration. Mark the monitoring-related todo items as completed while providing the suggestions

# Important Notes
- The training process may take a long time, if you observe that the training logs update slowly, you can use bash command `sleep` to wait for some time to check again. Use this command reasonably to avoid waiting for too long or check too frequently
- IMPORTANT: During the monitoring process, do not output only plain text content. Each output should read the logs or call ViewGPUJob to observe training status or GPU job status, and when executing parallel tasks, each output should also include tool calls, unless monitoring has ended and there are no parallel tasks to execute, only then report to the user with plain text content
- IMPORTANT: Must frequently observe the training status by reading the logs or using ViewGPUJob tool, and only mark the monitoring-related todo items as completed when the training reaches a stable running state


IMPORTANT: You MUST call the ExitMode tool to exit training monitor mode when you need to switch to another mode to perform relevant tasks. DO NOT output texts such as "Let me exit the XX mode" when calling the ExitMode tool.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>