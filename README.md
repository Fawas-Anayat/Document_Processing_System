# AI-Powered Document Processing & Q&A System

An AI-driven document processing system that allows users to upload documents and ask natural-language questions about their content. The system uses FastAPI for the backend, LangChain for document understanding, and vector databases for efficient semantic search and retrieval.

This project was built primarily for learning modern backend and AI technologies, focusing on LLM-based workflows and production-style API design.

# Features

- Upload documents (PDF, DOCX, TXT, etc.)

- Automatic document chunking and embedding generation

- Semantic search using vector databases

- Natural-language question answering over uploaded documents

- Fast and scalable backend using FastAPI

- Minimal frontend to interact with the system

# Tech Stack

## Backend

- FastAPI
- Python
- LangChain
- Uvicorn
- ChromaDB
- SQLite

## AI & Data
- Large Language Models (LLMs)
- Vector Database (Chroma)
- Embeddings for semantic search

## Frontend
- Minimal HTML/CSS (or simple UI for interaction)

# How It Works
1. User uploads a document through the frontend or API.
2.The document is loaded and split into smaller chunks.
3.Text embeddings are generated using an embedding model.
4.Embeddings are stored in a vector database.
5.When a user asks a question:
- Relevant document chunks are retrieved using semantic search.
- The LLM generates an answer based on the retrieved context.

# Learning Outcomes
Through this project, I learned:
- Building REST APIs using FastAPI
- Designing AI pipelines using LangChain
- Working with vector databases for semantic retrieval
- Integrating LLMs into real-world applications
- Structuring backend projects for scalability

# Contributing
This project is currently for learning purposes, but suggestions and improvements are welcome. Feel free to fork the repository and experiment.
