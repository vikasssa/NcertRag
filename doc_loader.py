from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus
import os


embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
vector_store = Milvus(embedding_function=embeddings,auto_id=True)

def load_files(dir_path):
    """Load and process all PDF files in the given directory."""
    try:
        files = [os.path.join(dir_path, file) for file in os.listdir(dir_path) if file.endswith('.pdf')]
        if not files:
            print(f"No PDF files found in directory: {dir_path}")
            return

        for file_path in files:
            print(f"Processing: {file_path}")
            loader = PyPDFLoader(file_path)
            docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200, add_start_index=True
            )
            all_splits = text_splitter.split_documents(docs)

            vector_store.add_documents(documents=all_splits)

        print("All files processed successfully.")

    except Exception as e:
        print(f"Error processing files: {e}")


if __name__ == "__main__":
    dir_path = 'book/'  # Adjust this to your directory path
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        load_files(dir_path)
    else:
        print(f"Directory not found: {dir_path}")