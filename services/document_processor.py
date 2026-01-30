# services/document_processor.py
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from typing import List, Dict
import os
import uuid
from config import settings

class DocumentProcessor:
    
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},  
            encode_kwargs={'normalize_embeddings': True}
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,  # Overlap to maintain context
            length_function=len,                    # How to measure length
            separators=["\n\n", "\n", " ", ""]     # Split on paragraphs first, then sentences
        )
        
        os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True)
    
    def load_document(self, file_path: str, file_type: str) -> List :
        
        if file_type == "pdf":
            loader = PyPDFLoader(file_path)
            
        elif file_type == "docx":
            loader = Docx2txtLoader(file_path)
            
        elif file_type == "txt":
            loader = TextLoader(file_path, encoding='utf-8')
            
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        return loader.load()
    
    def process_and_store_document(
        self, 
        file_path: str, 
        file_type: str, 
        user_id: int,
        document_id: int
    ) -> Dict :
        try:
            documents = self.load_document(file_path, file_type)

            chunks = self.text_splitter.split_documents(documents)

            collection_name = f"user_{user_id}_doc_{document_id}_{uuid.uuid4().hex[:8]}"
            
            vector_store = Chroma.from_documents(
                documents=chunks,                          # The text chunks
                embedding=self.embeddings,                 # The embedding model
                collection_name=collection_name,           # Unique name for this doc
                persist_directory=settings.CHROMA_DB_DIR  # Where to save
            )
            
            print(f"Successfully processed document. Collection: {collection_name}")
            
            return {
                "collection_name": collection_name,
                "chunk_count": len(chunks),
                "status": "success"
            }
            
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            raise Exception(f"Failed to process document: {str(e)}")
    
    def get_vector_store(self, collection_name: str):
        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=settings.CHROMA_DB_DIR
        )
    
    def delete_vector_store(self, collection_name: str) -> bool:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
            
            client.delete_collection(name=collection_name)
            print(f"Deleted collection: {collection_name}")
            return True
            
        except Exception as e:
            print(f"Error deleting collection: {str(e)}")
            return False

document_processor = DocumentProcessor()