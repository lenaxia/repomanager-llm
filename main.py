import json
import logging
from datetime import datetime, timezone, timedelta
import asyncio
import yaml
from github import Github, GithubException
from utils import get_issues, update_last_run_timestamp, load_yaml_workflow, get_all_comments, retrieve_context, create_and_cache_embeddings
from llm import llm_request
from actions import perform_action, log_action

# Load configuration
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize GitHub client
g = Github(config['github_token'])

# Repository details
owner = config['owner']
repo_name = config['repo_name']
repository = g.get_repo(f'{owner}/{repo_name}')

# Main orchestrator function
async def main_orchestrator(first_pass_mode=False):
    last_run_timestamp = datetime.fromisoformat(config['last_run_timestamp']).replace(tzinfo=timezone.utc)
    
    if first_pass_mode:
        issues = get_issues()
    else:
        issues = get_issues(since=last_run_timestamp)
    
    workflows = load_yaml_workflow('workflows')
    deprecate_v4_workflow = load_yaml_workflow('workflows/deprecate_v4_issues.yaml')
    move_setup_workflow = load_yaml_workflow('workflows/move_setup_issues_to_discussion.yaml')
    workflows.extend(deprecate_v4_workflow)
    workflows.extend(move_setup_workflow)
    
    # Ensure embeddings are cached for all URLs specified in the workflows
    all_urls = set()
    for workflow in workflows:
        for step in workflow['steps']:
            if step['type'] == 'retrieve_context':
                all_urls.update(step['urls'])
    
    await asyncio.gather(*[create_and_cache_embeddings(url) for url in all_urls])
    
    for issue in issues:
        # Fetch and prepare data
        comments = get_all_comments(issue)
        created_date = issue.created_at
        last_modified_date = issue.updated_at
        is_pull_request = isinstance(issue, g.get_pull(issue.number))
        labels = [label.name for label in issue.labels]
        
        # Calculate age and staleness
        age = (datetime.now(timezone.utc) - created_date).days
        staleness = (datetime.now(timezone.utc) - last_modified_date).days
        
        data = {
            'title': issue.title,
            'body': issue.body,
            'comments': comments,
            'created_date': created_date.isoformat(),
            'last_modified_date': last_modified_date.isoformat(),
            'is_pull_request': is_pull_request,
            'labels': labels,
            'age': age,
            'staleness': staleness
        }
        
        for workflow in workflows:
            for step in workflow['steps']:
                if step['type'] == 'llm':
                    prompt = step['prompt'].format(**data)
                    output_schema = step['output_schema']
                    response = await llm_request(prompt, output_schema)
                    data.update(response)
                
                if step['type'] == 'retrieve_context':
                    urls = step['urls']
                    context = await retrieve_context(urls, issue.title, issue.body, data.get('category', 'no'))
                    data['context'] = context
                
                if 'actions' in step:
                    for action in step['actions']:
                        condition = action['condition']
                        if eval(condition, {}, data):
                            for sub_step in action['steps']:
                                if config['test_mode']:
                                    log_action(issue, sub_step, data)
                                else:
                                    await perform_action(issue, sub_step, data)
                            
                            next_action = action.get('next_action', 'break')
                            if next_action == 'break':
                                break
                            else:
                                # Find the next action by name
                                next_action_step = next((s for s in step['actions'] if s['name'] == next_action), None)
                                if next_action_step:
                                    for sub_step in next_action_step['steps']:
                                        if config['test_mode']:
                                            log_action(issue, sub_step, data)
                                        else:
                                            await perform_action(issue, sub_step, data)
                                    break
                                else:
                                    logging.warning(f"Next action '{next_action}' not found for issue #{issue.number}")

    # Update the last run timestamp
    if not first_pass_mode:
        update_last_run_timestamp(datetime.now(timezone.utc).isoformat())

if __name__ == "__main__":
    # Run in first pass mode if needed
    first_pass_mode = config.get('first_pass_mode', False)
    asyncio.run(main_orchestrator(first_pass_mode=first_pass_mode))
