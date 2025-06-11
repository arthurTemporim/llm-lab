#!/bin/bash

# Check if .env exists in the current directory
if [ ! -f .env ]; then
    if [ -f example.env ]; then
        cp example.env .env
        echo ".env file was not found. example.env copied to .env."
    else
        echo "Neither .env nor example.env found. Please provide an example.env file."
        exit 1
    fi
else
    echo ".env file already exists."
fi

