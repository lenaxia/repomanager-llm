import logging
from github import Github, GithubException

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to perform actions on issues
async def perform_action(issue, action, data):
    try:
        action_type = action['type']
        if action_type == 'comment':
            content = action['content'].format(**data)
            issue.create_comment(content)
            logging.info(f"Commented on issue #{issue.number}: {content}")
        elif action_type == 'label':
            labels = action['labels']
            issue.add_to_labels(*labels)
            logging.info(f"Tagged issue #{issue.number} with labels: {', '.join(labels)}")
        elif action_type == 'close':
            issue.edit(state='closed')
            logging.info(f"Closed issue #{issue.number}")
        elif action_type == 'convert_to_discussion':
            issue.create_comment("/discussion")
            logging.info(f"Converted issue #{issue.number} to discussion")
        else:
            logging.warning(f"Unsupported action type: {action_type}")
    except GithubException as e:
        logging.error(f"Failed to perform action on issue #{issue.number}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while performing action on issue #{issue.number}: {e}")

# Function to log actions in test mode
def log_action(issue, action, data):
    action_type = action['type']
    if action_type == 'comment':
        content = action['content'].format(**data)
        logging.info(f"Test Mode: Would have commented on issue #{issue.number}: {content}")
    elif action_type == 'label':
        labels = action['labels']
        logging.info(f"Test Mode: Would have tagged issue #{issue.number} with labels: {', '.join(labels)}")
    elif action_type == 'close':
        logging.info(f"Test Mode: Would have closed issue #{issue.number}")
    elif action_type == 'convert_to_discussion':
        logging.info(f"Test Mode: Would have converted issue #{issue.number} to discussion")
    else:
        logging.warning(f"Unsupported action type: {action_type}")
    
    # Write the action to the test output file
    with open(config['test_output_file'], 'a') as test_file:
        test_file.write(f"Issue #{issue.number} - Action: {action_type}\n")
        if action_type == 'comment':
            test_file.write(f"Content: {content}\n")
        elif action_type == 'label':
            test_file.write(f"Labels: {', '.join(labels)}\n")
        elif action_type == 'close':
            test_file.write("Closed the issue\n")
        elif action_type == 'convert_to_discussion':
            test_file.write("Converted the issue to a discussion\n")
        test_file.write("\n")
