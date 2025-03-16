# LLM Batch Processing

This repository provides wrapped batch processing workflows for **OpenAI** and **Mistral AI**, enabling efficient handling of large-scale language model (LLM) requests.

**## 🚀 Features**
- Simplified batch processing for OpenAI and Mistral AI models.
- Optimized request handling to improve API efficiency.
- Easily customizable for various LLM-powered applications.

**## 📦 Installation**
Clone this repository using:
```bash
git clone https://github.com/your-username/LLM_batch_process.git
cd LLM_batch_process

## 🛠 How to Use

Before importing packages, ensure you have set your `OPENAI_API_KEY` or `MISTRAL_API_KEY` as an environment variable.

### 1️⃣ Import the Batch Processor

#### OpenAI Batch API
```python
from openai_batch import OpenAIBatchProcessor

#### Mistral AI Batch API
```python
from mistral_batch import MistralAIBatchProcessor

### 2️⃣ Create a Batch Processor

#### OpenAI Batch API Example
```python
batch_processor = OpenAIBatchProcessor(
    model_name="gpt-4o",  # Specify the model
    max_tokens=300,  # Set the maximum output tokens          
    temperature=0.5,  # Optional: Default temperature is 0.1          
    filename_prefix="my_openai_task",  # Optional: Set a filename prefix for your tasks
    task_dir="openai_batch_tasks",  # Optional: Folder to save full tasks (auto-created if not exists)
    batch_dir="openai_batch_jobs",  # Optional: Folder for separated batch jobs (auto-created if not exists)
    output_dir="openai_batch_outputs"  # Optional: Folder for batch outputs (auto-created if not exists)
)


