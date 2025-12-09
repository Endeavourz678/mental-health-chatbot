"""
Data loading and preprocessing utilities for Mental Health Chatbot
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents a document for the vector store"""
    content: str
    metadata: Dict
    doc_id: str


class DataLoader:
    """Handles loading and preprocessing of mental health datasets"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
    
    def load_qa_dataset(self, filename: str = "dataset_qa.csv") -> List[Document]:
        """
        Load QA dataset and convert to documents for RAG
        
        Args:
            filename: Name of the QA CSV file
            
        Returns:
            List of Document objects
        """
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            logger.warning(f"QA dataset not found at {filepath}")
            return []
        
        try:
            df = pd.read_csv(filepath, header=None, names=['id', 'question', 'answer', 'intent'])
            documents = []
            
            for idx, row in df.iterrows():
                # Skip rows that are intent summaries
                if str(row['question']).startswith('Intent '):
                    continue
                
                # Create document combining Q&A
                content = f"Question: {row['question']}\nAnswer: {row['answer']}"
                
                doc = Document(
                    content=content,
                    metadata={
                        'source': 'qa_dataset',
                        'intent': row['intent'],
                        'question': row['question'],
                        'answer': row['answer'],
                        'type': 'qa_pair'
                    },
                    doc_id=f"qa_{idx}"
                )
                documents.append(doc)
            
            logger.info(f"Loaded {len(documents)} QA pairs from {filename}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading QA dataset: {e}")
            return []
    
    def load_statements_dataset(self, filename: str = "dataset_statements.csv") -> List[Document]:
        """
        Load statements dataset with mental health labels
        
        Args:
            filename: Name of the statements CSV file
            
        Returns:
            List of Document objects
        """
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Statements dataset not found at {filepath}")
            return []
        
        try:
            df = pd.read_csv(filepath)
            documents = []
            
            # Handle different column name formats
            statement_col = 'statement' if 'statement' in df.columns else df.columns[1]
            status_col = 'status' if 'status' in df.columns else df.columns[2]
            
            for idx, row in df.iterrows():
                content = str(row[statement_col])
                status = str(row[status_col])
                
                doc = Document(
                    content=content,
                    metadata={
                        'source': 'statements_dataset',
                        'mental_health_status': status,
                        'type': 'statement'
                    },
                    doc_id=f"stmt_{idx}"
                )
                documents.append(doc)
            
            logger.info(f"Loaded {len(documents)} statements from {filename}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading statements dataset: {e}")
            return []
    
    def load_all_datasets(self) -> List[Document]:
        """Load all available datasets"""
        all_documents = []
        
        # Load QA dataset
        qa_docs = self.load_qa_dataset()
        all_documents.extend(qa_docs)
        
        # Load statements dataset if exists
        stmt_docs = self.load_statements_dataset()
        all_documents.extend(stmt_docs)
        
        logger.info(f"Total documents loaded: {len(all_documents)}")
        return all_documents
    
    def get_training_data_for_classification(self, filename: str = "dataset_statements.csv") -> Tuple[List[str], List[str]]:
        """
        Get training data for classification model
        
        Returns:
            Tuple of (texts, labels)
        """
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            return [], []
        
        try:
            df = pd.read_csv(filepath)
            statement_col = 'statement' if 'statement' in df.columns else df.columns[1]
            status_col = 'status' if 'status' in df.columns else df.columns[2]
            
            texts = df[statement_col].astype(str).tolist()
            labels = df[status_col].astype(str).tolist()
            
            return texts, labels
            
        except Exception as e:
            logger.error(f"Error getting training data: {e}")
            return [], []


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks
    
    Args:
        text: Input text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            for sep in ['. ', '! ', '? ', '\n']:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1:
                    end = start + last_sep + len(sep)
                    break
        
        chunks.append(text[start:end].strip())
        start = end - overlap
    
    return chunks
