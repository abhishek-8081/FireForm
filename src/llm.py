import json
import os
import requests
from requests.exceptions import Timeout, RequestException


class LLM:
    def __init__(self, transcript_text: str=None, target_fields: list=None, json_dict: dict=None, model: str=None):
        self._transcript_text = transcript_text
        self._target_fields = target_fields
        self._json = json_dict if json_dict is not None else {}
        # Optional per-request model override; falls back to OLLAMA_MODEL env.
        self._model = model

    def build_prompt(self, current_field: str, current_type: str = "string"):
        """
        This method is in charge of the prompt engineering. It creates a specific prompt for each target field.
        @params: current_field -> represents the current element of the json that is being prompted.
        @params: current_type  -> hint to the LLM about the expected value shape (date, number, etc.).
        """
        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
        with open(prompt_path, "r") as f:
            template = f.read()

        return template.format(field=current_field, type=current_type, text=self._transcript_text)

    def main_loop(self):
        timeout = 45
        max_retries = 3

        total_fields = len(self._target_fields)
        for i, (field, field_type) in enumerate(self._target_fields.items(), 1):
            prompt = self.build_prompt(field, field_type if isinstance(field_type, str) else "string")
            ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
            ollama_url = f"{ollama_host}/api/generate"
            ollama_model = self._model or os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

            payload = {
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
            }

            json_data = None
            try:
                for attempt in range(max_retries):
                    try:
                        response = requests.post(ollama_url, json=payload, timeout=timeout)
                        response.raise_for_status()
                        json_data = response.json()
                        break
                    except Timeout:
                        print(f"[LOG]: Ollama request timed out (attempt {attempt+1}) for field '{field}'. Retrying...")
                    except RequestException as e:
                        print(f"[LOG]: Ollama request failed: {e}")
            except requests.exceptions.ConnectionError:
                raise ConnectionError(
                    f"Could not connect to Ollama at {ollama_url}. "
                    "Please ensure Ollama is running and accessible."
                )
            except requests.exceptions.HTTPError as e:
                raise RuntimeError(f"Ollama returned an error: {e}")

            if json_data is None:
                raise RuntimeError("Failed to get response from Ollama after retries.")
            else:
                parsed_response = json_data["response"]
                self.add_response_to_json(field, parsed_response)
                print(f"[{i}/{total_fields}] Extracted data for field '{field}' successfully.")

        print("----------------------------------")
        print("\t[LOG] Resulting JSON created from the input text:")
        print(json.dumps(self._json, indent=2))
        print("--------- extracted data ---------")

        return self

    def add_response_to_json(self, field: str, value: str):
        """
        this method adds the following value under the specified field,
        or under a new field if the field doesn't exist, to the json dict
        """
        value = value.strip().replace('"', "")
        parsed_value = None

        if value != "-1":
            parsed_value = value

        if field in self._json.keys():
            self._json[field].append(parsed_value)
        else:
            self._json[field] = parsed_value

        return


    def get_data(self):
        return self._json
