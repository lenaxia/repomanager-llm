import json
import os
from datetime import datetime, timezone
from github import Github, GithubException
import aiohttp
import asyncio
from sentence_transformers import SentenceTransformer, util
import pickle
import logging

# Load configuration
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize sentence transformer model for embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to get issues
def get_issues(since=None):
    try:
        g = Github(config['github_token'])
        repo = g.get_repo(f'{config["owner"]}/{config["repo_name"]}')
        if since:
            return repo.get_issues(state='open', since=since)
        else:
            return repo.get_issues(state='open')
    except GithubException as e:
        logging.error(f"Failed to fetch issues: {e}")
        return []

# Function to get all comments, handling pagination
def get_all_comments(issue):
    try:
        comments = []
        for comment in issue.get_comments():
            comments.append({
                'id': comment.id,
                'body': comment.body,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat(),
                'user': comment.user.login
            })
        return comments
    except GithubException as e:
        logging.error(f"Failed to fetch comments for issue #{issue.number}: {e}")
        return []

# Function to load YAML workflows
def load_yaml_workflow(workflows_dir):
    workflows = []
    for filename in os.listdir(workflows_dir):
        if filename.endswith('.yaml'):
            with open(os.path.join(workflows_dir, filename), 'r') as file:
                workflow = yaml.safe_load(file)
                workflows.append(workflow)
    return workflows

# Function to update last run timestamp
def update_last_run_timestamp(timestamp):
    config['last_run_timestamp'] = timestamp
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)
    logging.info(f"Updated last run timestamp to {timestamp}")

# Function to get cached embeddings
def get_cached_embeddings(urls):
    cache_file = 'embeddings_cache.pkl'
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            cache = pickle.load(f)
    else:
        cache = {}
    
    embeddings = []
    for url in urls:
        if url in cache:
            embeddings.append(cache[url])
        else:
            text = asyncio.run(fetch_document_text(url))
            chunks = chunk_document(text)
            chunk_embeddings = model.encode(chunks)
            cache[url] = chunk_embeddings
            embeddings.append(chunk_embeddings)
    
    with open(cache_file, 'wb') as f:
        pickle.dump(cache, f)
    
    return embeddings

# Function to fetch document text
async def fetch_document_text(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text()
            else:
                logging.error(f"Failed to fetch document from {url}: {response.status} {await response.text()}")
                return ""

# Function to chunk document text
def chunk_document(text, chunk_size=config['chunk_size']):
    words = text.split()
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks

# Function to create and cache embeddings for a document
async def create_and_cache_embeddings(url):
    cache_file = 'embeddings_cache.pkl'
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            cache = pickle.load(f)
    else:
        cache = {}
    
    if url not in cache:
        text = await fetch_document_text(url)
        chunks = chunk_document(text)
        chunk_embeddings = model.encode(chunks)
        cache[url] = chunk_embeddings
        with open(cache_file, 'wb') as f:
            pickle.dump(cache, f)
        logging.info(f"Created and cached embeddings for document {url}")
    else:
        logging.debug(f"Embeddings for document {url} already exist in cache")

# Function to retrieve relevant context based on embeddings
async def retrieve_context(urls, title, body, category, retrieval_threshold=config['retrieval_threshold']):
    embeddings = await get_cached_embeddings(urls)
    query = f"Title: {title}\nBody: {body}\nCategory: {category}"
    query_embedding = model.encode(query)
    
    relevant_context = []
    for url_embeddings in embeddings:
        for chunk_embedding in url_embeddings:
            similarity = util.pytorch_cos_sim(query_embedding, chunk_embedding).item()
            if similarity > retrieval_threshold:
                relevant_context.append(chunk_embedding)
    
    return relevant_context
