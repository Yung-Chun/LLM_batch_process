# LLM Batch Processing

This repository provides wrapped batch processing workflows for **OpenAI** and **Mistral AI**, enabling efficient handling of large-scale language model (LLM) requests.

**## 🚀 Features**
- Simplified batch processing for OpenAI and Mistral AI models.
- Optimized request handling to improve API efficiency.
- Easily customizable for various LLM-powered applications.

**## 📦 Installation**
Clone this repository using:
```bash
git clone https://github.com/Yung-Chun/LLM_batch_process.git
cd LLM_batch_process
```

## 🛠 How to Use

Before importing packages, ensure you have set your `OPENAI_API_KEY` or `MISTRAL_API_KEY` as an environment variable.

### 1️⃣ Import the Batch Processor

#### OpenAI Batch API
```python
from openai_batch import OpenAIBatchProcessor
```

#### Mistral AI Batch API
```python
from mistral_batch import MistralAIBatchProcessor
```

### 2️⃣ Create a Batch Processor

#### OpenAI Batch API Example
```python
batch_processor = OpenAIBatchProcessor(
    model_name="gpt-4o",  # Specify the model
    max_completion_tokens=300,  max_completion_tokens=300,  # Optional: The default value is `None`. According to OpenAI, the maximum is 4096.
    temperature=0.5,  # Optional: Default temperature is 1          
    filename_prefix="my_openai",  # Optional: Set a filename prefix for your tasks
    task_dir="openai_batch_tasks",  # Optional: Folder to save full tasks (auto-created if not exists)
    batch_dir="openai_batch_jobs",  # Optional: Folder for separated batch jobs (auto-created if not exists)
    output_dir="openai_batch_outputs"  # Optional: Folder for batch outputs (auto-created if not exists)
)
```
For Mistral AI, simply replace `OpenAIBatchProcessor` with `MistralAIBatchProcessor`. Both processors share the same configuration structure, as shown below.

### 3️⃣ Create Tasks and Save

Define a list of IDs and messages, then save them as a `.jsonl` file. Each task will be written as a single JSON object per line. 
Each message can include multiple prompts, such as **system**, **user**, and **assistant**.

```python
tasks = batch_processor.create_task(ids, messages)
batch_processor.write_task_file(tasks)
```

### 4️⃣~7️⃣ Split, Upload, and Run Batch Jobs

Split tasks into batch files, upload them, and initiate jobs via **OpenAI** or **Mistral AI** APIs.

#### 🔹 Set the Batch Size

Ensure your batch size doesn't exceed the rate limit of your subscription tier:

```python
batch_size = 20000
num_files = (len(tasks) + batch_size - 1) // batch_size
print(f'Total requests: {len(tasks)}. Batch size: {batch_size}. Separated into {num_files} files.')
```

#### 🔹 Iterate Through Batches

For each batch:
- `write_batch_file()` saves the split tasks as a `.jsonl` file.  
- `upload_batch_file()` uploads it to the selected provider.  
- `create_batch_job()` initiates the job.  
- `check_batch_job_status()` monitors job completion and proceeds to the next. All batches will be processed sequentially. You can adjust `check_interval` (in minutes) to control how often the job status is checked.

```python
# Iterate over chunks of data
for i in range(num_files):
    print(f"Processing batch {i+1}/{num_files}...", end="\n\n")

    start_index = i * batch_size
    end_index = min(start_index + batch_size, len(tasks))  # Avoid out-of-range slicing

    # Slice the list to get the current batch
    batch_data = tasks[start_index:end_index]

    # Ensure we are not writing an empty batch
    if not batch_data:
        print(f"Skipping batch {i+1} as it's empty.")
        continue

    # Generate batch ID using current time
    batch_id = int(time())

    # Write batch tasks
    batch_processor.write_batch_file(batch_data, batch_id)
    print(f"Batch {batch_id} written successfully.", end="\n\n")
    
    # Upload batch file
    batch_file = batch_processor.upload_batch_file(batch_id)
    if not batch_file:
        print(f"Failed to upload file for batch {batch_id}. Skipping this batch.")
        continue  # Instead of breaking, we skip and move to the next batch

    # Create batch job
    batch_job = batch_processor.create_batch_job(batch_file)
    if not batch_job:
        print(f"Failed to create batch job for batch {batch_id}. Skipping this batch.")
        continue

    # Monitor batch job status until completion
    final_status = batch_processor.check_batch_job_status(batch_job.id, check_interval=8)
    print(f"Batch job {batch_job.id} finished with status: {final_status}")

print("\nBatch processing completed.")
```

### 8️⃣ Save Batch Output

Use `save_batch_output()` to save the output of each completed batch as a `.json` file.  

> ⚠️ **Note:** OpenAI’s `limit` argument in `.list()` may not work as expected. Instead of relying on it, stop listing batches manually by checking for a specific `batch.id` in your [dashboard](https://platform.openai.com/).

```python
output_files = []

# Iterate through batches starting from the most recent
for batch in batch_processor.client.batches.list():
    
    if batch.id == 'batch_67da91ed3b608190bee3c797f0137e6c':  # 🔁 Replace with your stopping batch ID
        break

    print(f"Batch ID: {batch.id}, Status: {batch.status}")

    # Collect only completed batches
    if batch.status == "completed":
        batch_id, created_at, output_file_id = batch.id, batch.created_at, batch.output_file_id
        output_files.append([batch_id, created_at, output_file_id])

print(f"Total completed batches retrieved: {len(output_files)}")
```

Then, save outputs from each completed batch:

```python
for i, (batch_id, created_at, output_file_id) in enumerate(output_files):
    print(f"Processing completed batch {batch_id}")
    batch_processor.save_batch_output(output_file_id)
```

✅ This ensures that only **completed** batches are downloaded and saved. Failed or canceled jobs will be skipped.
