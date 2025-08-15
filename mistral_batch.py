# Copyright (c) 2025 Yung-Chun Chen
# Licensed under the MIT License. See LICENSE file in the project root for details.

import json
import os
import time
import re
from pathlib import Path
from glob import glob
from mistralai import Mistral
from typing import List, Dict

class MistralAIBatchProcessor:
    def __init__(self, model_name: str, max_tokens: int, temperature: float = 0.1, 
                 filename_prefix: str = 'mistral', task_dir: str = 'mistral_batch_tasks', batch_dir: str = 'mistral_batch_jobs', output_dir: str = 'mistral_batch_outputs'):
        # Access environment variable
        self.api_key = os.getenv("MISTRAL_API_KEY")  # Retrieve the API_KEY set earlier
        if not self.api_key:
            print("Error: MISTRAL_API_KEY is not set as an environment variable.")
        self.client = Mistral(api_key=self.api_key)
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.filename_prefix = filename_prefix
        self.task_dir = task_dir
        self.batch_dir = batch_dir
        self.output_dir = output_dir

    def create_task(self, id: str, messages: list) -> dict:
        return {
            "custom_id": str(id),
            "body": {
                "model": self.model_name,
                "max_tokens": self.max_tokens,
                "messages": messages,
            },
        }

    def write_task_file(self, tasks: List[Dict]):
        file_path = Path(self.task_dir) / f"{self.filename_prefix}_tasks.jsonl"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('w', encoding='utf-8') as f:
            for obj in tasks:
                f.write(json.dumps(obj) + '\n')

    def write_batch_file(self, requests: List[Dict], i: int):
        file_path = Path(self.batch_dir) / f"{self.filename_prefix}_batch_job{str(i)}.jsonl"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if not requests:
            print(f"Warning: No requests to write for batch {i}.")

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
        file_path = f"{self.batch_dir}/{filename}"

        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist. Cannot upload.")
            return None

        print(f'Uploading batch file: {file_path}')
        try:
            batch_file = self.client.files.upload(
                file={
                    "file_name": file_path,
                    "content": open(file_path, "rb")},
                purpose="batch"
            )

            print(f'Successfully uploaded file. Batch file ID: {batch_file.id}')
            return batch_file

        except FileNotFoundError:
            print(f"Error: File {file_path} was not found during upload.")
        except IOError as error:
            print(f"File IO error while uploading {file_path}: {error}")
        except Exception as e:
            print(f"Unexpected error while uploading file {file_path}: {e}")

        return None  # Return None if upload fails

    def create_batch_job(self, batch_file, endpoint: str = "/v1/chat/completions"):
        print('Creating batch job...')
        try:
            batch_job = self.client.batch.jobs.create(
                input_files=[batch_file.id],
                model=self.model_name,
                endpoint=endpoint,
                # metadata={"job_type": "testing"}
            )

            print(f'Batch job ID: {batch_job.id}')
            return batch_job
        except Exception as e:
            print(f"Error creating batch job: {e}")
            return None

    def check_batch_job_status(self, batch_job_id: str, check_interval: int = 3) -> str:
        success_status = {'SUCCESS'}
        failed_statuses = {'FAILED', 'TIMEOUT_EXCEEDED', 'CANCELLED'}
        processing_statuses = {'QUEUED', 'RUNNING', 'CANCELLATION_REQUESTED', 'CANCELLATION_REQUESTED'}
        while True:
            try:
                batch_job = self.client.batch.jobs.get(job_id=batch_job_id)
                status = batch_job.status
                if status in success_status:
                    print(f"Batch job {batch_job.id} finished with status: {status}")
                    return status
                elif status in failed_statuses:
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

    
        output_file_name = f"{self.filename_prefix}_batch_output{output_file_id}.json"
        file_path = path / output_file_name

        print(f"Saving batch output to: {file_path}")

        try:
            output_file = self.client.files.download(file_id=output_file_id)
            with open(file_path, "w") as f:
                for chunk in output_file.stream:
                    f.write(chunk.decode("utf-8"))

            print(f"Batch output {output_file_id} saved successfully.")

        except IOError as error:
            print(f"Error writing batch output to file {file_path}: {error}")
        except Exception as e:
            print(f"Unexpected error in save_batch_output: {e}")