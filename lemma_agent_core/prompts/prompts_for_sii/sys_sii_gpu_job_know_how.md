# Model Training with GPUs

You are given three tools for creating GPU jobs, tracking their status and stopping them. But you should be careful with the system architecture described below and follow the instructions here to do tasks which requires GPUs.

### The System Architecture of the Computing Cluster

You have the access to a computing cluster that contains a CPU machine and a GPU cluster:

- The CPU machine is where you are working now, so the working directory is in this CPU machine. The CPU machine has the access to the Internet, but has no GPU resources.
- The GPU cluster can only be accessed via GPU related tools (CreateGPUJob, ViewGPUJob and StopGPUJob). The GPU cluster has no access to the Internet.
- The CPU machine and the GPU cluster share the storage system.

Thus, you should download models and datasets, setting up the environment in this CPU machine as it has the access to the Internet, and do model training and inference via the GPU related tools.


### Best Practice for Tasks Requiring GPUs

#### Prepare model, data, and code

You should do the following work in this CPU machine before creating the GPU jobs:
- Download model checkpoints and datasets
- Setup conda environment
- Write code files and config files
- Preprocess the data if the processing doesn't need GPUs
- Write training or inference scripts for creating GPU jobs

**IMPORTANT**: Make sure you installed the GPU version of torch if needed. The GPU cluster has installed CUDA of version 12.8.
**IMPORTANT**: You should add enough logging in the code and script, and specify log files for checking the job progress.

#### Creating and Tracking GPU Jobs

Use CreateGPUJob tool to create a GPU job, and use ViewGPUJob tool to check the status of the job. Be aware of that:

- ViewGPUJob can only check the job status, it cannot access to the detailed information of the GPUs
- You should track the job progress in the log file you have specified
- You should be patient as the training will be slow. Stop the job Only when the log shows failure or invalid results
- Do not check with `nvidia-smi` for GPU status, because GPUs are not in this CPU machine!
- **IMPORTANT**: Do not use BashOutput tool for checking the job status, this job is not running in this CPU machine!

