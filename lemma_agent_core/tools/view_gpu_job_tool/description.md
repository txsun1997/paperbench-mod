Checks the status and details of a distributed GPU training job using the job ID.

# Purpose

This tool allows you to monitor GPU jobs that were created using the CreateGPUJob tool. It retrieves real-time information about the job's current state, progress, and any output or errors.

# System Context

The agent operates on a CPU server that shares a storage disk with the GPU cluster. GPU jobs run asynchronously on the cluster, so this tool is essential for:
- Checking if a job has started, is running, or has completed
- Monitoring training progress and performance metrics
- Debugging failed jobs by viewing error logs
- Verifying resource allocation (GPU count, instance count)

# Usage

Simply provide the `job_id` that was returned when you created the job using CreateGPUJob.

**Example:**
```json
{
  "job_id": "job-abc123def456"
}
```

# What Information is Retrieved

It will return job status:
- job_queuing: The job is waiting in the queue to be created
- job_creating: The cluster is creating the job
- job_running: The job is running
- job_succeeded: The job has completed successfully
- job_stopped: The job has been stopped

# Integration with Other Tools

- Use **CreateGPUJob** first to submit a job and receive a job_id
- Use **ViewGPUJob** (this tool) to monitor the job's progress
- Use **StopGPUJob** if you need to terminate a running or pending job
- Use **Read** tool to examine output files and logs saved to the shared directory
