Stops a running or pending distributed GPU training job using the job ID.

# Purpose

This tool terminates a GPU job that was created using the CreateGPUJob tool. Use this when:
- Training metrics show the model is not learning properly
- You discovered an error in the configuration or code
- You want to free up GPU resources for a different job
- The job is stuck or running longer than expected
- You need to make changes and restart with different parameters

# System Context

The agent operates on a CPU server that shares a storage disk with the GPU cluster. GPU jobs run asynchronously on GPU servers, and this tool sends a termination signal to the cluster to stop the specified job gracefully.

# Usage

Provide the `job_id` of the job you want to stop. Optionally include a `reason` for better tracking.

**Example 1: Basic stop**
```json
{
  "job_id": "job-abc123def456"
}
```

**Example 2: Stop with reason**
```json
{
  "job_id": "job-abc123def456",
  "reason": "Loss is not decreasing after 5 epochs, need to adjust learning rate"
}
```

# When to Use StopGPUJob

**Good Reasons to Stop a Job:**
- Training loss is not decreasing or is diverging (NaN/Inf)
- Validation metrics show no improvement after many epochs
- Discovered a bug in the training script
- Wrong hyperparameters or model configuration
- Need to modify data preprocessing
- Accidentally started the same job multiple times
- Job is consuming resources but not making progress (hung process)

**When NOT to Use:**
- Job has already completed - stopping has no effect
- Job has already failed - already terminated
- Job is in final stages and will complete soon - consider waiting

# Best Practices

1. **Check Status First**: Use ViewGPUJob to verify the job is actually running before stopping
2. **Provide Reason**: Include a reason parameter to document why the job was stopped
3. **Verify Checkpoints**: Before stopping, ensure the job has saved recent checkpoints if you want to resume later
4. **Wait for Confirmation**: After stopping, use ViewGPUJob again to confirm the status changed to "stopped"
5. **Clean Up Resources**: If the job created temporary files, consider cleaning them up after stopping

# Integration with Other Tools

- Use **CreateGPUJob** to submit jobs and receive job_id
- Use **ViewGPUJob** to check if a job should be stopped (monitor metrics, status)
- Use **StopGPUJob** (this tool) to terminate the job
- Use **ViewGPUJob** again after stopping to confirm termination
- Use **Read** tool to examine partial results or logs from the stopped job

# Typical Workflow

```
1. Create job with CreateGPUJob → receives job_id: "job-123"
2. Monitor with ViewGPUJob → notice training is not progressing well
3. Decide to stop the job
4. Use StopGPUJob with job_id: "job-123" and reason
5. Confirm with ViewGPUJob → status should be "stopped"
6. Fix the issue (code, hyperparameters, etc.)
7. Create a new job with CreateGPUJob
```

# Important Notes

- **Immediate Effect**: The stop request is processed immediately, but actual termination may take a few seconds
- **No Undo**: Stopped jobs cannot be restarted; you must create a new job
- **Data Safety**: Ensure important data is checkpointed before stopping long-running jobs
- **Multiple Instances**: For distributed jobs with multiple instances, all instances will be stopped
- **Grace Period**: Some clusters may allow processes a few seconds to cleanup before forceful termination

