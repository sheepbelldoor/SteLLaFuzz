# SteLLaFuzz

SteLLaFuzz

## Folder structure
```
SteLLaFuzz
├── aflnet: a modified version of AFLNet which outputs states and state transitions 
├── analyse.sh: analysis script 
├── benchmark: a modified version of ProfuzzBench
│   └── subjects/<subject>
│       ├── LLM: LLM-related files of SteLLaFuzz
│       ├── utility: utility file of SteLLaFuzz
│       └── stellafuzz.py: SteLLaFuzz implementation for the subject
├── clean.sh: clean script
├── ChatAFL: the source code of ChatAFL
├── SteLLaFuzz: the source code of SteLLaFuzz, same as aflnet
├── deps.sh: the script to install dependencies, asks for the password when executed
├── README: this file
├── run.sh: the execution script to run fuzzers on subjects and collect data
└── setup.sh: the preparation script to set up docker images
```

## 1. Setup and Usage

### 1.1. Installing Dependencies

`Docker`, `Bash`, `Python3` with `pandas` and `matplotlib` libraries. We provide a helper script `deps.sh` which runs the required steps to ensure that all dependencies are provided:

```bash
./deps.sh
```

### 1.2. Preparing Docker Images [~60 minutes]

Run the following command to set up all docker images, including the subjects with all fuzzers:

```bash
KEY=<OPENAI_API_KEY> ./setup.sh
```

The process is estimated to take about 60 minutes. OPENAI_API_KEY is your OpenAI key and please refer to [this](https://openai.com/) about how to obtain a key.

### 1.3. Running Experiments

Utilize the `run.sh` script to run experiments. The command is as follows:

```bash
 ./run.sh <container_number> <fuzzed_time> <subjects> <fuzzers>
```

Where `container_number` specifies how many containers are created to run a single fuzzer on a particular subject (each container runs one fuzzer on one subject). `fuzzed_time` indicates the fuzzing time in minutes. `subjects` is the list of subjects under test, and `fuzzers` is the list of fuzzers that are utilized to fuzz subjects. For example, the command (`run.sh 1 5 pure-ftpd stellafuzz`) would create 1 container for the fuzzer SteLLaFuzz to fuzz the subject pure-ftpd for 5 minutes. In a short cut, one can execute all fuzzers and all subjects by using the writing `all` in place of the subject and fuzzer list.

When the script completes, in the `benchmark` directory a folder `result-<name of subject>` will be created, containing fuzzing results for each run.

### 1.4. Analyzing Results

The `analyze.sh` script is used to analyze data and construct plots illustrating the average code and state coverage over time for fuzzers on each subject. The script is executed using the following command:

```bash
./analyze.sh <subjects> <fuzzed_time> 
```

The script takes in 2 arguments - `subjects` is the list of subjects under test and `fuzzed_time` is the duration of the run to be analyzed. Note that, the second argument is optional and the script by default will assume that the execution time is 1440 minutes, which is equal to 1 day. For example, the command (`analyze.sh exim 240`) will analyze the first 4 hours of the execution results of the exim subject.

Upon completion of execution, the script will process the archives by construcing csv files, containing the covered number of branches, states, and state transitions over time. Furthermore, these csv files will be processed into PNG files which are plots, illustrating the average code and state coverage over time for fuzzers on each subject (`cov_over_time...` for the code and branch coverage, `state_over_time...` for the state and state transition coverage). All of this information is moved to a `res_<subject name>` folder in the root directory with a timestamp.

### 1.5. Cleaning Up

When the evaluation of the artifact is completed, running the `clean.sh` script will ensure that the only leftover files are in this directory:

```bash
./clean.sh
```

## 2. Functional Analysis

The source code for the LLM is located in `benchmark/subjects/<subject>/LLM` and `benchmark/subjects/<subject>/stellafuzz.py`.

The responses of the LLM for strategies can be found in `llm_outputs` directory in the result folder of a run.

## 3. Customization

### 3.1. Enhancing or experimenting with SteLLaFuzz

If a modification is done to any of the fuzzers, re-executing `setup.sh` will rebuild all the images with the modified version. All provided versions of SteLLaFuzz contain a Dockerfile, allowing for the checking of build failures in the same environment as the one for the subjects and having a clean image, where one can setup different subjects.

### 3.2. Tuning fuzzer parameters

All parameters, used in the experiments are located in `benchmark/subjects/<subject>/utility/utility.py`. The parameters, specific to SteLLaFuzz are:

* MODEL: the model to use for the LLM, default is `gpt-4o-mini`
* SEQUENCE_REPEAT: the number of times to repeat the test case generation, default is `1`
* LLM_RETRY: the number of times to retry the LLM, default is `3`

## 4. License

This artifact is licensed under the Apache License 2.0 - see the [LICENSE](./LICENSE) file for details.
