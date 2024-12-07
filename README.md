# GitHub Repository Manager with LLM Integration

## Overview

This repository contains a Python-based tool designed to manage GitHub issues and pull requests using a Language Model (LLM). The tool can categorize issues, retrieve relevant context from documents, and perform actions based on predefined workflows.

## Features

- **Categorize Issues**: Automatically categorize GitHub issues using an LLM.
- **Retrieve Context**: Fetch relevant context from external documents based on the issue's title, body, and category.
- **Perform Actions**: Execute predefined actions such as adding labels, commenting, closing issues, or converting them to discussions.
- **Test Mode**: Run the tool in a test mode to log actions without actually performing them on GitHub.

## Prerequisites

- Python 3.8 or higher
- A GitHub Personal Access Token (PAT) with appropriate permissions
- An LLM API endpoint and model

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/repomanager-llm.git
   cd repomanager-llm
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the tool:
   - Copy `config.json.example` to `config.json` and fill in the necessary details:
     ```json
     {
       "github_token": "your_github_pat_here",
       "owner": "owner_username",
       "repo_name": "repository_name",
       "llm_endpoint": "https://api.openai.com/v1/engines/text-davinci-003/completions",
       "llm_model": "text-davinci-003",
       "first_pass_mode": false,
       "last_run_timestamp": "2024-12-05T23:44:00Z",
       "retrieval_threshold": 0.7,
       "max_tokens": 500,
       "chunk_size": 512,
       "max_retries": 3,
       "retry_delay_seconds": 5,
       "test_mode": true,
       "test_output_file": "test_output.log"
     }
     ```

## Usage

### Running the Tool

1. Run the tool in normal mode:
   ```bash
   python main.py
   ```

2. Run the tool in first pass mode (to process all open issues):
   ```bash
   python main.py --first_pass_mode
   ```

3. Run the tool in test mode (logs actions without performing them):
   ```bash
   python main.py --test_mode
   ```

### Workflows

Workflows are defined in the `workflows` directory. Each workflow is a YAML file that specifies a series of steps to be executed. Here is an example of a workflow:

```yaml
name: RAG-Based Workflow
steps:
  - name: Categorize Issue
    type: llm
    prompt: |
      Analyze the following GitHub issue:
      Title: {title}
      Body: {body}
      Categorize this issue as 'bug', 'triage', 'feature request', or 'no'. Respond with a JSON object containing only a "category" key with a value from the above list.
    output_schema: |
      {
        "category": "bug|triage|feature request|no"
      }
    actions:
      - name: Categorize
        condition: "category != 'no'"
        steps:
          - type: label
            labels: ["{category}"]
        next_action: "Check for Response"
      - name: No Category
        condition: "category == 'no'"
        steps:
          - type: comment
            content: "This issue does not fall into a defined category. Please provide more details."
        next_action: "break"

  - name: Check for Response
    type: llm
    prompt: |
      Analyze the following GitHub issue:
      Title: {title}
      Body: {body}
      Does this issue warrant a response based on the following criteria: [list of criteria]. Respond with a JSON object containing only a "response_warranted" key with a value of "yes" or "no".
    output_schema: |
      {
        "response_warranted": "yes|no"
      }
    actions:
      - name: Generate Response
        condition: "response_warranted == 'yes'"
        steps:
          - type: retrieve_context
            urls: ["https://example.com/doc1.pdf", "https://example.com/doc2.pdf"]
          - type: generate_response
            prompt: |
              Generate a response to the following GitHub issue:
              Title: {title}
              Body: {body}
              Category: {category}
              Context: {context}
          - type: comment
            content: "{response}"
        next_action: "break"
      - name: No Response
        condition: "response_warranted == 'no'"
        steps:
          - type: comment
            content: "This issue does not warrant a response based on the defined criteria."
        next_action: "break"
```

#### Workflow YAML Schema

The workflow YAML files follow a specific schema to define the steps and actions to be executed. Here is the full schema definition:

```yaml
name: string  # Name of the workflow
steps:
  - name: string  # Name of the step
    type: string  # Type of the step (e.g., 'llm', 'retrieve_context', 'generate_response', 'comment', 'label', 'close', 'convert_to_discussion')
    prompt: string  # Prompt for the LLM request (only if type is 'llm')
    output_schema: string  # JSON schema for validating the LLM response (only if type is 'llm')
    urls: list  # List of URLs to fetch context from (only if type is 'retrieve_context')
    actions:
      - name: string  # Name of the action
        condition: string  # Condition to check before executing the action
        steps:
          - type: string  # Type of the sub-step (e.g., 'comment', 'label', 'close', 'convert_to_discussion')
            content: string  # Content for the comment (only if type is 'comment')
            labels: list  # List of labels to add (only if type is 'label')
        next_action: string  # Name of the next action to execute (optional, default is 'break')
```

### Configuration

The `config.json` file contains various configuration parameters that control the behavior of the tool. Here is a detailed explanation of each parameter:

- **`github_token`**: Your GitHub Personal Access Token. This token is used to authenticate requests to the GitHub API.
- **`owner`**: The GitHub username or organization that owns the repository. This is used to identify the repository.
- **`repo_name`**: The name of the GitHub repository. This is used to identify the repository.
- **`llm_endpoint`**: The endpoint for the LLM API. This is the URL where the LLM requests are sent.
- **`llm_model`**: The model to use for the LLM API. This specifies the model that the LLM should use for generating responses.
- **`first_pass_mode`**: A boolean flag to indicate whether the tool should process all open issues. Set to `true` to process all open issues, otherwise `false`.
- **`last_run_timestamp`**: The timestamp of the last run. This is used to fetch issues that have been updated since the last run.
- **`retrieval_threshold`**: The similarity threshold for retrieving context. This is used to determine if a chunk of text is relevant based on its similarity score.
- **`max_tokens`**: The maximum number of tokens to use in LLM requests. This limits the length of the input and output text for the LLM.
- **`chunk_size`**: The size of text chunks for embedding. This determines how large each chunk of text will be when creating embeddings.
- **`max_retries`**: The maximum number of retries for LLM requests. This specifies how many times the tool should retry an LLM request if it fails.
- **`retry_delay_seconds`**: The delay between retries for LLM requests. This specifies the time to wait between retries.
- **`test_mode`**: A boolean flag to indicate whether the tool should run in test mode. Set to `true` to log actions without performing them on GitHub.
- **`test_output_file`**: The file to log test actions. This specifies the file where test actions will be logged.

### Data Object

The data object passed to the workflows contains the following fields:

- **`title`**: The title of the GitHub issue.
- **`body`**: The body of the GitHub issue.
- **`comments`**: A list of comments on the issue, each with `id`, `body`, `created_at`, `updated_at`, and `user`.
- **`created_date`**: The ISO 8601 formatted creation date of the issue.
- **`last_modified_date`**: The ISO 8601 formatted last modified date of the issue.
- **`is_pull_request`**: A boolean indicating whether the issue is a pull request.
- **`labels`**: A list of labels associated with the issue.
- **`age`**: The age of the issue in days.
- **`staleness`**: The staleness of the issue in days.
- **`category`**: The category of the issue as determined by the LLM (if applicable).
- **`context`**: The relevant context retrieved from external documents (if applicable).

### Actions and Step Types

The following actions and step types can be used in the workflows:

- **`comment`**: Adds a comment to the issue.
  - **`content`**: The content of the comment. Supports template variables.
- **`label`**: Adds labels to the issue.
  - **`labels`**: A list of labels to add. Supports template variables.
- **`close`**: Closes the issue.
- **`convert_to_discussion`**: Converts the issue to a discussion.
- **`llm`**: Sends a request to the LLM API.
  - **`prompt`**: The prompt to send to the LLM. Supports template variables.
  - **`output_schema`**: The JSON schema to validate the LLM response.
- **`retrieve_context`**: Retrieves relevant context from external documents.
  - **`urls`**: A list of URLs to fetch context from. Supports template variables.
- **`generate_response`**: Generates a response to the issue using the LLM.
  - **`prompt`**: The prompt to generate the response. Supports template variables.

### Example Workflow

Here is an example of a workflow that uses the available actions and step types:

```yaml
name: RAG-Based Workflow
steps:
  - name: Categorize Issue
    type: llm
    prompt: |
      Analyze the following GitHub issue:
      Title: {title}
      Body: {body}
      Categorize this issue as 'bug', 'triage', 'feature request', or 'no'. Respond with a JSON object containing only a "category" key with a value from the above list.
    output_schema: |
      {
        "category": "bug|triage|feature request|no"
      }
    actions:
      - name: Tag and Close
        condition: "category != 'no'"
        steps:
          - type: label
            labels: ["{category}"]
        next_action: "Check for Response"
      - name: No Category
        condition: "category == 'no'"
        steps:
          - type: comment
            content: "This issue does not fall into a defined category. Please provide more details."
        next_action: "break"

  - name: Check for Response
    type: llm
    prompt: |
      Analyze the following GitHub issue:
      Title: {title}
      Body: {body}
      Does this issue warrant a response based on the following criteria: [list of criteria]. Respond with a JSON object containing only a "response_warranted" key with a value of "yes" or "no".
    output_schema: |
      {
        "response_warranted": "yes|no"
      }
    actions:
      - name: Generate Response
        condition: "response_warranted == 'yes'"
        steps:
          - type: retrieve_context
            urls: ["https://example.com/doc1.pdf", "https://example.com/doc2.pdf"]
          - type: generate_response
            prompt: |
              Generate a response to the following GitHub issue:
              Title: {title}
              Body: {body}
              Category: {category}
              Context: {context}
          - type: comment
            content: "{response}"
        next_action: "break"
      - name: No Response
        condition: "response_warranted == 'no'"
        steps:
          - type: comment
            content: "This issue does not warrant a response based on the defined criteria."
        next_action: "break"
```

### Directory Structure

```
repomanager-llm/
├── .gitignore
├── README.md
├── actions.py
├── config.json
├── embeddings_cache.pkl
├── llm.py
├── main.py
├── requirements.txt
├── utils.py
└── workflows/
    └── rag_based_workflow.yaml
    └── deprecate_v4_issues.yaml
    └── move_setup_issues_to_discussion.yaml
```

## Contributing

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push your changes to your fork.
5. Open a pull request to the main repository.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact

For any questions or issues, please open an issue in the repository or contact the maintainer at [your-email@example.com](mailto:your-email@example.com).

### Directory Structure

```
repomanager-llm/
├── .gitignore
├── README.md
├── actions.py
├── config.json
├── embeddings_cache.pkl
├── llm.py
├── main.py
├── requirements.txt
├── utils.py
└── workflows/
    └── rag_based_workflow.yaml
```

## Contributing

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push your changes to your fork.
5. Open a pull request to the main repository.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact

For any questions or issues, please open an issue in the repository or contact the maintainer at [your-email@example.com](mailto:your-email@example.com).

