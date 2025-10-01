#!/usr/bin/env python3

# Standard library
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import time

# Third-party libraries
import colorama
from colorama import Fore, Style
from jsonpointer import JsonPointer, JsonPointerException
from openpyxl import load_workbook, Workbook
import requests
from tqdm import tqdm

# Initialize colorama
colorama.init()

def print_info(msg):
    print(f"{Fore.BLUE}[+] {msg}{Style.RESET_ALL}")

def print_warning(msg):
    print(f"{Fore.YELLOW}[!] {msg}{Style.RESET_ALL}")

def print_error(msg):
    print(f"{Fore.RED}[!] {msg}{Style.RESET_ALL}")

def print_success(msg):
    print(f"{Fore.GREEN}[+] {msg}{Style.RESET_ALL}")

def ascii_art():
    art = """
  ____  __.__                  .__               
 |    |/ _|  |__ _____    ____ |__| ____ _____   
 |      < |  |  \\__  \\  /    \\|  |/    \\__  \\  
 |    |  \\|   Y  \\/ __ \\|   |  \\  |   |  \\/ __ \\_
 |____|__ \\___|  (____  /___|  /__|___|  (____  /
         \\/    \\/     \\/     \\/        \\/     \\/ 

    """
    print(Fore.GREEN + art + Style.RESET_ALL)

# Main function
def main():
    parser = argparse.ArgumentParser(
        description="Khaniña - LLM Prompt Injection Fuzzer",
        epilog="This tool sends prompts from Excel files to an LLM API endpoint and collects responses for analysis. Use verbose mode for detailed output during prompt processing."
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output, showing detailed progress for each prompt including index out of total and response times')
    args = parser.parse_args()

    ascii_art()
    print_info("Welcome to Khaniña - LLM Prompt Injection Fuzzer")

    # Check for config files
    headers_file = Path('resources/headers.json')
    body_file = Path('resources/body.json')

    if not headers_file.exists() or not body_file.exists():
        print_warning("Configuration files not found. Entering preparation phase.")
        print_info("Please copy resources/headers.json.example to resources/headers.json and modify with your endpoint details.")
        print_info("Please copy resources/body.json.example to resources/body.json and modify with your request body (or leave empty for GET).")
        print_info("Also, place your prompt Excel files in the 'prompts' directory.")
        return

    # Load configs
    try:
        with open(headers_file) as f:
            headers_config = json.load(f)
        with open(body_file) as f:
            body_config = json.load(f)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in config files: {e}")
        return

    # Validate essential fields
    if 'base_url' not in headers_config:
        print_error("headers.json must contain 'base_url' field.")
        return
    if not headers_config['base_url'].startswith('http') and not headers_config['base_url'].startswith('https'):
        print_error("The 'base_url' in headers.json must be a URL starting with http or https.")
        return
    if 'endpoint' not in headers_config:
        print_error("headers.json must contain 'endpoint' field.")
        return
    if not headers_config['endpoint'].startswith('/'):
        print_error("The 'endpoint' in headers.json must start with '/'.")
        return
    if 'method' not in headers_config:
        print_error("headers.json must contain 'method' field.")
        return
    if headers_config['method'].upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
        print_error("Invalid HTTP method in headers.json.")
        return
    if not isinstance(headers_config.get('headers', {}), dict):
        print_error("'headers' in headers.json must be a JSON object.")
        return
    if "{{PROMPT}}" not in json.dumps(body_config):
        print_warning("body.json does not contain '{{PROMPT}}' placeholder. Ensure your prompt is inserted correctly.")
        # Choice to continue or not
        cont = input("Do you want to continue? (y/n): ").strip().lower()
        if cont != 'y':
            print_info("Operation cancelled.")
            return

    if args.verbose:
        print_info("Configuration files loaded successfully.")

    # Display details
    print_info("Endpoint Details:")
    print(f"  Method: {headers_config.get('method')}")
    print(f"  Base URL: {headers_config.get('base_url')}")
    print(f"  Endpoint: {headers_config.get('endpoint')}")
    print(f"  Headers: {json.dumps(headers_config.get('headers', {}), indent=2)}")
    print_info("Request Body:")
    print(f"  {json.dumps(body_config, indent=2)}")

    confirm = input("Do you want to proceed with these settings? (y/n): ").strip().lower()
    if confirm != 'y':
        print_info("Operation cancelled.")
        return

    # Project management
    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)
    existing_projects = [d.name for d in results_dir.iterdir() if d.is_dir()]

    if existing_projects:
        print_info("Existing projects:")
        for i, proj in enumerate(existing_projects, 1):
            print(f"  {i}. {proj}")
        choice = input("Choose an existing project (number) or 'n' for new: ").strip()
        if choice.lower() == 'n':
            project_name = input("Enter new project name (lowercase alphanum only): ").strip()
            if not re.match(r'^[a-z0-9]+$', project_name):
                print_error("Invalid project name. Must be lowercase alphanum.")
                return
        else:
            try:
                project_name = existing_projects[int(choice) - 1]
            except (ValueError, IndexError):
                print_error("Invalid choice.")
                return
    else:
        project_name = input("Enter new project name (lowercase alphanum only): ").strip()
        if not re.match(r'^[a-z0-9]+$', project_name):
            print_error("Invalid project name. Must be lowercase alphanum.")
            return

    project_dir = results_dir / project_name
    project_dir.mkdir(exist_ok=True)

    # JSON pointer
    pointer = input("Enter JSON pointer for main key-value extraction (e.g., /choices/0/message/content): ").strip()

    # Prompt selection
    prompts_dir = Path('prompts')
    if not prompts_dir.exists():
        print_error("Prompts directory not found.")
        return

    prompt_files = list(prompts_dir.glob('*.xlsx'))
    if not prompt_files:
        print_error("No Excel files found in prompts directory.")
        return

    print_info("Available prompt files:")
    for i, pf in enumerate(prompt_files, 1):
        print(f"  {i}. {pf.name}")
        # Display first few prompts
        try:
            wb = load_workbook(pf)
            ws = wb.active
            if ws is not None:
                prompts = [ws.cell(row=r, column=2).value for r in range(2, min(6, ws.max_row + 1)) if ws.cell(row=r, column=2).value]
                print(f"    Sample prompts: {', '.join(str(p)[:50] for p in prompts[:3])}")
            else: 
                print_warning(f"No active sheet in {pf.name}")
        except Exception as e:
            print_warning(f"Error reading {pf.name}: {e}")

    selected_indices = input("Enter file numbers to use (comma-separated, or 'all'): ").strip()
    if selected_indices.lower() == 'all':
        selected_files = prompt_files
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selected_indices.split(',')]
            selected_files = [prompt_files[i] for i in indices if 0 <= i < len(prompt_files)]
        except ValueError:
            print_error("Invalid selection.")
            return

    # Process each selected file
    for pf in selected_files:
        print_info(f"Processing {pf.name}")
        try:
            wb = load_workbook(pf)
            ws = wb.active
            if ws is not None:
                prompts = [ws.cell(row=r, column=2).value for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=2).value]
            else:
                print_warning(f"No active sheet in {pf.name}, skipping.")
                continue
        except Exception as e:
            print_error(f"Error reading prompts from {pf.name}: {e}")
            continue

        # Create results Excel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"{pf.stem} - {project_name} - {timestamp} - Results.xlsx"
        result_path = project_dir / result_filename
        result_wb = Workbook()
        result_ws = result_wb.active
        if result_ws is not None:
            result_ws.append(['Index', 'Prompt', 'Main', 'Full Response', 'Response Time (s)'])
        else:
            print_error(f"Failed to create results worksheet for {pf.name}, skipping.")
            continue

        if not args.verbose:
            pbar = tqdm(total=len(prompts), desc="Processing prompts")

        for idx, prompt in enumerate(prompts, 1):
            if not isinstance(prompt, str):
                prompt = str(prompt)

            if args.verbose:
                print_info(f"Sending prompt {idx}/{len(prompts)}: {prompt[:50]}...")

            # Prepare request
            method = headers_config.get('method').upper()
            url = headers_config.get('base_url') + headers_config.get('endpoint')
            headers = headers_config.get('headers', {})
            body = body_config.copy()
            # Place prompt in body if placeholder exists, replace all occurrences, at least once
            body_str = json.dumps(body)
            body_str = body_str.replace("{{PROMPT}}", prompt)
            try:
                body = json.loads(body_str)
            except json.JSONDecodeError:
                print_error("Error inserting prompt into request body.")
                continue

            start_time = time.time()
            try:
                if method == 'GET':
                    response = requests.get(url, headers=headers, params=body)
                else:
                    response = requests.request(method, url, headers=headers, json=body)
                response_time = time.time() - start_time

                if response.status_code == 200:
                    try:
                        resp_json = response.json()
                        main_value = JsonPointer(pointer).get(resp_json)
                        full_resp = json.dumps(resp_json)
                    except (JsonPointerException, json.JSONDecodeError):
                        main_value = "Error extracting"
                        full_resp = response.text
                else:
                    main_value = f"HTTP {response.status_code}"
                    full_resp = response.text

                result_ws.append([idx, prompt, main_value, full_resp, response_time])

                if args.verbose:
                    print_success(f"Response received in {response_time:.2f}s")

            except Exception as e:
                print_error(f"Error sending request for prompt {idx}: {e}")
                result_ws.append([idx, prompt, "Error", str(e), 0])

            if not args.verbose:
                pbar.update(1)

        if not args.verbose:
            pbar.close()

        result_wb.save(result_path)
        print_success(f"Results saved to {result_path}")

    print_success("All processing complete. Goodbye!")

if __name__ == "__main__":
    main()
