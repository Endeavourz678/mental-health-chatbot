import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import hashlib

from utils.data_loader import Document


logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        persist_directory: str,
        collection_name: str,
        openai_api_key: str,
        embedding_model: str = "text-embedding-3-small"
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"Initialized vector store with collection: {collection_name}")
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using OpenAI
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def _generate_doc_id(self, content: str, metadata: Dict) -> str:
        """Generate unique document ID based on content"""
        hash_input = f"{content}{str(metadata)}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def add_documents(self, documents: List[Document], batch_size: int = 100) -> int:
        """
        Add documents to the vector store
        
        Args:
            documents: List of Document objects
            batch_size: Number of documents to process at once
            
        Returns:
            Number of documents added
        """
        if not documents:
            logger.warning("No documents to add")
            return 0
        
        added_count = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            contents = [doc.content for doc in batch]
            ids = [doc.doc_id or self._generate_doc_id(doc.content, doc.metadata) for doc in batch]
            metadatas = [doc.metadata for doc in batch]
            
            try:
                existing = self.collection.get(ids=ids)
                new_indices = [
                    j for j, doc_id in enumerate(ids) 
                    if doc_id not in existing['ids']
                ]
                
                if not new_indices:
                    continue
                
                new_contents = [contents[j] for j in new_indices]
                new_ids = [ids[j] for j in new_indices]
                new_metadatas = [metadatas[j] for j in new_indices]
                
                embeddings = self._get_embeddings(new_contents)
                
                self.collection.add(
                    documents=new_contents,
                    embeddings=embeddings,
                    ids=new_ids,
                    metadatas=new_metadatas
                )
                
                added_count += len(new_indices)
                logger.info(f"Added batch of {len(new_indices)} documents")
                
            except Exception as e:
                logger.error(f"Error adding batch: {e}")
                continue
        
        logger.info(f"Total documents added: {added_count}")
        return added_count
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        threshold: float = 0.0
    ) -> List[Dict]:
        """
        Search for similar documents
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            threshold: Minimum similarity score (0-1, higher is more similar)
            
        Returns:
            List of search results with content, metadata, and scores
        """
        try:
            query_embedding = self._get_embeddings([query])[0]
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata
            )
            
            formatted_results = []
            
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i] if results['distances'] else 0
                    similarity = 1 - distance
                    
                    if similarity >= threshold:
                        formatted_results.append({
                            'content': doc,
                            'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                            'id': results['ids'][0][i] if results['ids'] else None,
                            'similarity': similarity
                        })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []
    
    def search_qa_pairs(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search specifically for QA pairs"""
        return self.search(
            query=query,
            top_k=top_k,
            filter_metadata={"type": "qa_pair"}
        )
    
    def search_similar_statements(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for similar mental health statements"""
        return self.search(
            query=query,
            top_k=top_k,
            filter_metadata={"type": "statement"}
        )
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection"""
        return {
            'name': self.collection_name,
            'count': self.collection.count(),
            'persist_directory': str(self.persist_directory)
        }
    
    def clear_collection(self) -> None:
        """Clear all documents from the collection"""
        try:
            self.chroma_client.delete_collection(self.collection_name)
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Cleared collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            raise