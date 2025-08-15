import json
import os
import time
import re
from pathlib import Path
from glob import glob
from openai import OpenAI
from typing import List, Dict

class OpenAIBatchProcessor:
    def __init__(self, model_name: str, max_completion_tokens: int = None, temperature: float = 1, 
                 filename_prefix: str = 'openai', task_dir: str = 'batch_tasks', batch_dir: str = 'batch_jobs', output_dir: str = 'batch_outputs'):
        # Access environment variable
        self.api_key = os.getenv("OPENAI_API_KEY")  # Retrieve the API_KEY set earlier
        if not self.api_key:
            print("Error: OPENAI_API_KEY is not set as an environment variable.")
        self.client = OpenAI(api_key=self.api_key)
        self.model_name = model_name
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.filename_prefix = filename_prefix
        self.task_dir = task_dir
        self.batch_dir = batch_dir
        self.output_dir = output_dir
        self.success_statuses = {'completed'}
        self.failed_statuses = {'failed', 'expired', 'cancelled'}
        self.statuses = {'completed', 'failed', 'expired', 'cancelled', 'validating', 'in_progress', 'finalizing', 'cancelling'}

    def create_task(self, ids: List, messages: List) -> List[Dict]:
        tasks = []
        for task_id, message in zip(ids, messages):  # Unpacking tuple directly
            tasks.append({
                "custom_id": str(task_id),
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": self.model_name,
                    "temperature": self.temperature,
                    "max_completion_tokens": self.max_completion_tokens,
                    "response_format": {"type": "json_object"},
                    "messages": [message],
                },
            })
        return tasks


    def write_task_file(self, tasks: List[Dict]):
        file_path = Path(self.task_dir) / f"{self.filename_prefix}_tasks.jsonl"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('w', encoding='utf-8') as f:
            for obj in tasks:
                f.write(json.dumps(obj) + '\n')

    def write_batch_file(self, requests: List[Dict], batch_id: int):
        file_path = Path(self.batch_dir) / f"{self.filename_prefix}_batch_job{batch_id}.jsonl"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if not requests:
            print(f"Warning: No requests to write for batch {batch_id}.")

        try:
            with file_path.open('w', encoding='utf-8') as file:
                for request in requests:
                    file.write(json.dumps(request) + '\n')
            print(f"File {file_path} created successfully with {len(requests)} requests.")
        except IOError as error:
            print(f"Error writing to file {file_path}: {error}")
        except Exception as e:
            print(f"Unexpected error in write_batch_file: {e}")


    def upload_batch_file(self, batch_id: int):
        filename = f"{self.filename_prefix}_batch_job{batch_id}.jsonl"
        file_path = Path(self.batch_dir) / filename

        if not file_path.exists():
            print(f"Error: File {file_path} does not exist. Cannot upload.")
            return None

        print(f'Uploading batch file: {file_path}')
        try:
            with file_path.open('rb') as file:
                batch_file = self.client.files.create(file=file, purpose="batch")  # OpenAI API expects a file object

            print(f'Successfully uploaded file. Batch file ID: {batch_file.id}')
            return batch_file

        except FileNotFoundError:
            print(f"Error: File {file_path} was not found during upload.")
        except IOError as error:
            print(f"File IO error while uploading {file_path}: {error}")
        except Exception as e:
            print(f"Unexpected error while uploading file {file_path}: {e}")

        return None  # Return None if upload fails


    def create_batch_job(self, batch_file, endpoint: str = "/v1/chat/completions", completion_window: str = "24h"):
        print('Creating batch job...')
        try:
            batch_job = self.client.batches.create(
                input_file_id=batch_file.id,
                endpoint=endpoint,
                completion_window=completion_window
            )
            print(f'Batch job ID: {batch_job.id}')
            return batch_job
        except Exception as e:
            print(f"Error creating batch job: {e}")
            return None

    def check_batch_job_status(self, batch_job_id: str, check_interval: int = 3) -> str:
        while True:
            try:
                batch_job = self.client.batch.jobs.get(job_id=batch_job_id)
                status = batch_job.status
                if status in self.success_status:
                    print(f"Batch job {batch_job.id} finished with status: {status}")
                    return status
                elif status in self.failed_statuses:
                    print(f"Batch job {batch_job.id} ended with status: {status}. Moving to the next batch.")
                    return status
                print(f"Current status: {status}. Checking again in {check_interval} minutes...")
                time.sleep(check_interval * 60)
            except Exception as e:
                print(f"Error checking status: {e}, retrying...")
                time.sleep(check_interval * 60)
    
    def save_batch_output(self, output_file_id: str):
        """Saves batch output files to the specified directory with a sequential ID."""
        path = Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
    
        output_file_name = f"{self.filename_prefix}_batch_output_{output_file_id}.json"
        file_path = path / output_file_name

        print(f"Saving batch output to: {file_path}")

        try:
            result = self.client.files.content(output_file_id).content  # Retrieve file content from OpenAI API

            with file_path.open("wb") as file:
                file.write(result)

            print(f"Batch output {output_file_id} saved successfully.")

        except IOError as error:
            print(f"Error writing batch output to file {file_path}: {error}")
        except Exception as e:
            print(f"Unexpected error in save_batch_output: {e}")
