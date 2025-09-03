## Prerequisite
<details>
<summary>Click to expand</summary>

- Install Python 3.12.11

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
uv venv .venv
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

Create `.env` file in the root of this repo and set the following variables (see `.env_template` for the template):
- `VAR_A`: Description of var_a
</details>


## Run the tests

<details>
<summary>Click to expand</summary>

- Integration tests
```bash 
make test
```

</details>

## Run the demo
<details>
<summary>Click to expand</summary>

- Start Docker

- Go to the root of this project and run:

```bash 
make docker_up
```

- Activate the virtual environment:

```bash 
source .venv/bin/activate
```

- Run the demo:
```bash 
make demo
```

</details>


## Others
<details>
<summary>Click to expand</summary>

- Name the branch with the name of the ticket you are working on. For instance, if you are working on the `KB-3` ticket, name the branch `KB-3`:

```bash 
git checkout -b KB-3
```


</details>