-- Create a new database named langflow
CREATE DATABASE langflow;

-- Connect to the langflow database
\c langflow;

-- Create the extension in the langflow database
CREATE EXTENSION IF NOT EXISTS vector;

-- Back to the default database setup (if needed)
--\c postgres;

-- Ensure the extension exists in the default database
--CREATE EXTENSION IF NOT EXISTS vector;

-- Create the embeddings table in the default database
/*
CREATE TABLE IF NOT EXISTS embeddings (
  id SERIAL PRIMARY KEY,
  embedding vector,
  text text,
  created_at timestamptz DEFAULT now()
);
*/
