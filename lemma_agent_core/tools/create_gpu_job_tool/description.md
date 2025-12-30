Creates a distributed GPU training job on the GPU cluster with specified GPU specifications and bash commands. This tool will return a job_id that can be used to monitor the job's status and stop the job.


**IMPORTANT NOTES**: You should always use this tool for running GPU tasks. The typical workflow is:
- Write and edit the code in the working directory
- Setup the environment in the working directory that can run GPU related jobs
- Download the model checkpoints and data in the working directory or to the path specified by the user
- Write the bash script for running GPU related jobs in the working directory
- Use this tool to submit the job
- Use the ViewGPUJob tool to monitor the job's status
- Use the StopGPUJob tool to stop the job if needed

- *IMPORTANT*: Add logging related command in the bash script, and you will Read the log file to track the GPU task progress!

# System Architecture

This CPU server shares a storage disk with the GPU cluster but **cannot directly use GPU resources**. To run GPU-intensive tasks (training, inference, etc.), you must submit jobs to the GPU cluster via CreateGPUJob tool. 

**DO NOT CHECK GPU STATUS IN THIS MACHINE, THIS MACHINE HAS NO GPUs!**

**Key Points:**
- The CPU server (where the agent runs) and GPU cluster share the same filesystem/working directory
- GPU servers can access all files in the current working directory
- GPU jobs are submitted via API and run asynchronously on the cluster
- Job status can be monitored using the ViewGPUJob tool
- The job can be stopped using the StopGPUJob tool

**GPU Cluster Architecture:**
- Each instance of the GPU cluster has maximum of 8 GPUs
- Each GPU is a NVIDIA GPU which has 141GB of memory

# Best Practices

**Recommended Workflow:**

1. **Assess GPU Requirements**: Determine the computational needs of the task
   - Consider model size, dataset size, and training complexity
   - Estimate the memory usage of the task and the GPU cluster to determine the appropriate gpu_count and instance_count
   - Decide on the appropriate gpu_count (1, 2, 4, or 8) and instance_count (1-8)
   - If the task requires less than or equal to 8 GPUs, YOU MUST ONLY USE 1 instance. Only if the task requires more than 8 GPUs, you can use multiple instances.
   - **CRITICAL**: If instance_count is greater than 1, the gpu_count will be forced to 8. So if you need to use more than 8 GPUs, you must use multiple instances.

2. **Prepare Training Script**: Write a bash script (e.g., `train.sh`) in the current working directory
   - **CRITICAL**: Use absolute paths for ALL files and directories within the script
   - Include all necessary setup commands (environment activation, dependency installation, etc.)
   - Include the actual training/inference command
   - Add logging and checkpointing as needed
   - Make sure the script is executable: `chmod +x train.sh`
   - Example: Use `/absolute/path/to/train.py` instead of `./train.py` or `train.py`

3. **Create GPU Job**: Use this tool to submit the job
   - Provide a descriptive name for easy identification
   - **CRITICAL**: Always use absolute paths in the command parameter
   - Set the command to execute your script with absolute path: `sh /absolute/path/to/train.sh`
   - The GPU cluster will execute this command in the shared working directory

4. **Monitor Job**: Use ViewGPUJob to check the status of your job

# Usage Examples

**Example 1: Single GPU training**
```json
{
  "name": "bert-base-training",
  "gpu_count": 1,
  "instance_count": 1,
  "command": "sh /workspace/experiments/train_bert.sh"
}
```

**Example 2: Training with 4 GPUs**
```json
{
  "name": "llama-finetuning",
  "gpu_count": 4,
  "instance_count": 1,
  "command": "sh /workspace/projects/llama/scripts/distributed_train.sh"
}
```

**Example 3: Large-scale training**
```json
{
  "name": "gpt-training-large",
  "gpu_count": 8,
  "instance_count": 2,
  "command": "bash /workspace/gpt/training/launch_distributed.sh"
}
```

# Parameters

- **name**: A unique, descriptive name for the job (e.g., "bert-finetuning-v1", "llama-inference-batch")
- **gpu_count**: Number of GPUs per instance (must be exactly 1, 2, 4, or 8)
  - Use 1 for small models or testing
  - Use 4 for medium-sized models
  - Use 8 for large models requiring extensive GPU memory
- **instance_count**: Number of GPU instances (1-8) for distributed training
  - Total GPUs = gpu_count × instance_count
  - Use multiple instances for data-parallel or model-parallel training
  - If instance_count is greater than 1, the gpu_count will be forced to 8
- **command**: The bash command to execute (must use absolute paths)
  - **CRITICAL**: Always use absolute paths: `sh /absolute/path/to/script.sh`
  - Can include arguments: `sh /workspace/train.sh --epochs 10 --batch-size 32`
  - Avoid relative paths like `./script.sh` or `scripts/train.sh`
  - Avoid inline commands; prefer well-structured scripts for reproducibility
  - All paths referenced within the script must also be absolute

# Notes

- Job execution is asynchronous; the tool returns immediately with a job_id
- Use ViewGPUJob with the returned job_id to monitor progress
- **Path Requirements**: 
  - The command parameter MUST use absolute paths
  - All paths within your bash scripts MUST be absolute
  - This ensures the GPU cluster can correctly locate files in the shared filesystem
  - Example: Use `/workspace/data/train.txt` instead of `data/train.txt` or `./data/train.txt`
- Ensure your training scripts save checkpoints to the shared directory (using absolute paths)
- Log files should also be written to the shared directory for debugging (using absolute paths)
- Use StopGPUJob if you need to terminate a running job

