#!/bin/sh

echo 'Waiting for Ollama to start...'
# Wait until Ollama API is reachable
until curl -s http://ollama:11434/api/tags > /dev/null; do
  sleep 2
done

echo 'Ollama started! Pulling model llama3.1...'
curl -X POST http://ollama:11434/api/pull -H "Content-Type: application/json" -d '{"model":"llama3.1"}'

echo 'Model pull request sent!'
