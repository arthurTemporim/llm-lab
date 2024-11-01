# llm-lab

A software lab about LLMs and others hype MLs.

This repo is organized as follows:

```sh
├── LICENSE
├── README.md
├── docs
├── modules
│   ├── langchain
│   ├── langflow
│   └── common-services
└── scripts
```

Move to each desired folder and follow each README.md about it to run and make tests.

## Development

* Simply run:

```sh
make init
```

* This will build and start `langflow`, `langchain` jupyter notebooks and `ollama` services, and download a model from on `scripts/ollama_pull_model.sh`.

* Acesss langchain on [http://localhost:7860/](http://localhost:7860/) and upload the file `langflow.json` to have a simple chatbot with local Ollama running on CPU or GPU.
