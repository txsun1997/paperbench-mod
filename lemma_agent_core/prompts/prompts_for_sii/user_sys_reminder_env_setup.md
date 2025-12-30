

<system-reminder>
Environment setup mode is active. The task requires a complex code excution environment. Please complete environment setup according to the task requirements and with the help of tools such as WebSearch.

Below are the best practices for environment setup, and you should follow them when you are conducting environment setup.

## Python/Conda Stack Setup Best Practices

You should be aware of the system architecture of the computing cluster. You are now setting up the environment in this CPU machine. If this task needs GPUs to run, you should setup the the environment for GPU as we mentioned before.

#### First: Ensure Conda is Present

Follow this workflow whenever you bring up a new machine or refresh the toolchain:

- System diagnostics: capture basic host info (`uname -a`, `lsb_release -a` or `sw_vers`). You don't need to check GPU availability as there are no GPUs in this CPU machine.
- Conda presence check: run `conda --version`. If Conda is not present, you need to install Miniforge.
- Miniforge install (when needed): download and install the latest Miniforge for your platform. For example, on Linux/MacOS, you can run the following commands:
```
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh
chmod +x Miniforge3-*.sh
./Miniforge3-*.sh -b -p $HOME/miniforge3
source $HOME/miniforge3/bin/activate
conda init --all
```

Reload the shell (`exec $SHELL`) and validate with `conda info`.


#### Second: Conda Environment Setup for The Task

Follow these best practices when preparing a Python/Conda stack for python-based tasks such as AI model training and evaluation:

- Check which conda env is currently activated with `conda info --envs`. The activated conda env will have a `*` next to the env name.
- If the user specifies an existing conda environment, you should use it by running `conda activate <env_name>`. Otherwise, you need to create a new conda env.
- If you need to create a new conda env, you should use `conda create -n <env_name> python=<python_version> -y`. Requirements for the env name and python version are as follows:
    - The env name should match the name of the task, so that we can easily identify the env for the task.
    - The python version should be at least 3.11.
- IMPORTANT: When you need to install packages into the conda env, you should use pip to install the packages.
- Be aware of that the GPU cluster has been installed with CUDA with version 12.8, so if you need to install torch, you can install with `pip install torch`, unless the user has specified a new version.
- Check whether there is a `requirements.txt` file in the task directory. If there is, you can use it to install the packages. Otherwise, you need to create a `requirements.txt` file first for better reproducibility.
    - List the packages that are required for the task in the `requirements.txt` file. You just need to list the core packages required packages here.
    - Install the packages into the conda env using `pip install -r requirements.txt`.
- We recommand to install `gputil` for logging GPU usages in the code

**Important Notes**:
- You should keep the conda env clean. Do not install packages that are not required for the task.
- Focus on the core packages that are absolutely necessary for the task, and install them first. You can install other packages later if necessary.
- If there are sub tasks have conflicting dependencies (e.g. model training and evaluation need different versions of the same package), you should create a new conda env for each sub task.
- IMPORTANT: If the network speed is very slow when installing dependencies, interrupt the installation and try switching to another installation source to complete the installation. If that does not work, interrupt your task and request the user to enter the VPN configuration to continue installing the environment.

IMPORTANT: You MUST call the ExitMode tool to exit environment setup mode when you need to switch to another mode to perform relevant tasks. DO NOT output texts such as "Let me exit the XX mode" when calling the ExitMode tool.
IMPORTANT: DO NOT mention the reminder content explicitly to the user.
</system-reminder>
