## Prerequisite
<details>
<summary>Click to expand</summary>

- Docker

- Install Python 3.12.11

- To assess the performance of the RAG Agent, create an account on [LangSmith](https://smith.langchain.com/) and generate a new key

</details>

## Configure the Python environment
<details>
<summary>Click to expand</summary>

- Install `uv`: 

```bash
pip install uv==0.8.14
```

- Create virtual environment: 
```bash
uv venv .venv --python 3.12.11
```

- Activate with: 
```bash
source .venv/bin/activate
```

- Install the libraries (including dev): 
```bash
uv pip install -r pyproject.toml --extra dev
```

- Install pre-commit: 
```bash
pre-commit install
```

</details>

## Configure the environment variables
<details>
<summary>Click to expand</summary>

Create `.env` file in the root of this repo and set the variables (see `.env.example` for the template).
</details>

## Generate assessment dataset for the RAG Agent
<details>
<summary>Click to expand</summary>

The script reads the raw input data, translates text into English, and generates a dataset of question–answer pairs plus open-ended follow-up questions. This dataset is intended to evaluate and benchmark the RAG agent's performance.

```bash 
make generate-assessment-dataset
```

</details>

## Docker

<details>
<summary>Click to expand</summary>

- Before building the docker image: 
    - update the image version in `pyproject.toml` under the `[project]` section as `version = "x.y.z"`.  
    - update the enviroment value `ENV` with either `dev` or `prod`.

- Build the docker image:
```bash 
make build-image
```

- Run the Docker Compose service with the image version specified in `pyproject.toml`:
```bash 
make compose-up
```

- Stop the Docker Compose service with the image version specified in `pyproject.toml`:
```bash 
make compose-down
```

</details>

## Run the tests

<details>
<summary>Click to expand</summary>

- Unit tests
```bash 
make unit-tests
```

Log in to [LangSmith](https://smith.langchain.com/), navigate to `Datasets & Experiments`, and review the test results.

</details>

## Run the demo
<details>
<summary>Click to expand</summary>


- Go to the root of this project and activate the virtual environment:

```bash 
source .venv/bin/activate
```

- Run the demo:
```bash 
make run-demo
```

</details>


## Interact with the API
<details>
<summary>Click to expand</summary>

- Start the uvicorn server: 
```bash
uvicorn app.api.v1.routers.main:app --reload --host 0.0.0.0 --port 8000
```

- Start a session:
```bash
curl -s http://127.0.0.1:8000/ | jq .
```

- Alternatively, start the session and save its session id in a shell variable:
```bash
session=$(curl -s http://127.0.0.1:8000/ | jq -r .session_id)
echo $session
```

- Check the status of the chatbot:
```bash
curl -s "http://127.0.0.1:8000/check_status?session_id=$session" | jq .
```

- Interact with the Agent:
```bash
curl -s -X POST "http://127.0.0.1:8000/rag-agent?session_id=$session" -H "Content-Type: application/json" -d '{"session_id":"'"$session"'","text":"What is the email address of the QSE Department?"}' | jq .
```

```bash
curl -s -X POST "http://127.0.0.1:8000/rag-agent?session_id=$session" -H "Content-Type: application/json" -d '{"session_id":"'"$session"'","text":"Where it is located?"}' | jq .
```

- Send feedback:
```bash
curl -s -X POST "http://127.0.0.1:8000/send_feedback" -H "Content-Type: application/json" -d '{"session_id":"'"$session"'","rating":5,"comments":"Works well"}' | jq .
```

</details>

## Others
<details>
<summary>Click to expand</summary>

- Name the branch with the name of the ticket you are working on. For instance, if you are working on the `KB-3` ticket, name the branch `KB-3`:

```bash 
git checkout -b KB-3
```

- When committing changes to your branch, use the key in your commit message to link those commits to the development panel in your Jira work item. For example: 

```bash
git commit -m "KB-3 <summary of commit>"
```

</details>