import json
import os
from time import sleep
import re
from pathlib import Path
from glob import glob
from openai import OpenAI
from typing import List, Dict

class OpenAIBatchProcessor:
    def __init__(self, model_name: str, max_tokens: int, temperature: float = 0.1, 
                 filename: str = 'my_file', task_dir: str = 'batch_tasks', batch_dir: str = 'batch_jobs', output_dir: str = 'batch_outputs'):
        self.client = OpenAI()
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.filename = filename
        self.task_dir = task_dir
        self.batch_dir = batch_dir
        self.output_dir = output_dir

    def create_task(self, id: str, messages: list) -> dict:
        return {
            "custom_id": str(id),
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.model_name,
                # "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"},
                "messages": messages,
            },
        }

    def write_task_file(self, tasks: List[Dict]):
        file_path = Path(self.task_dir) / f"{self.filename}_tasks.jsonl"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('w', encoding='utf-8') as f:
            for obj in tasks:
                f.write(json.dumps(obj) + '\n')

    def write_batch_file(self, requests: List[Dict], batch_id: int):
        file_path = Path(self.batch_dir) / f"{self.filename}_batch_job{batch_id}.jsonl"
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
        filename = f"{self.filename}_batch_job{batch_id}.jsonl"
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
        final_statuses = {'completed', 'failed', 'expired', 'cancelled'}
        while True:
            try:
                batch_job = self.client.batches.retrieve(batch_job_id)
                status = batch_job.status.lower()
                print(f"Current status: {status}")
                if status in final_statuses:
                    return status
                sleep(check_interval * 60)
            except Exception as e:
                print(f"Error checking status: {e}, retrying...")
                sleep(check_interval * 60)
    
    def save_batch_output(self, output_file_id: str):
        """Saves batch output files to the specified directory with a sequential ID."""
        path = Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)

    
        output_file_name = f"{self.filename}_batch_output_{output_file_id}.json"
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
