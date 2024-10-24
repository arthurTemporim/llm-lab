# LangFlow

Here there is configs and definitions about langflow.

- [LangFlow](https://www.langflow.org/pt/)

## Run

### Docker

To run locally using docker:

```sh
docker compose up --build -d
```

This will run these services:

```sh
NAMES
ollama
ollama-cpu
langflow
postgres
```

* Access `http://localhost:7860/` to see the main page of langflow

* Import simple projects using the UI and the file `modules/langflow/lang_flow.json`


#### Ollama

* [Ollama](https://ollama.com/)
* [Ollama api doc](https://github.com/ollama/ollama/blob/main/docs/api.md)
* [Ollama api pull model](https://github.com/ollama/ollama/blob/main/docs/api.md#pull-a-model)

* There will be 2 servers of **Ollama** running if you have all the docker+GPU configs, fell free to comment or remove ollama with gpu service of the docker-compose.
    * `http://localhost:11434/` - GPU
    * `http://localhost:11435/` - CPU

* On the langflow page you need to use the container netwrok names:
    * `http://ollama:11434` - GPU
    * `http://ollama-cpu:11434` - CPU


* After the ollama server is up, download a model. Note that the model only need to be dowloaded once, because the two ollama servers share the same docker volume.

```sh
curl http://localhost:11434/api/pull -d '{
  "name": "llama3.2"
}'
```

* Or run the scripts:

```sh
./scripts/ollama_pull_model.sh
```

* Send a message to verify if its working fine:

```sh
./scripts/ollama_send_pronpt.sh
```
