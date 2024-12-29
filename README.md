# NcertRAG



Description:
This POC demonstrates a system that processes PDF documents, converts their content into embeddings using HuggingFace's sentence transformer, and stores them in a Milvus vector database. The workflow involves a PDF processing service that extracts, splits, and embeds text from PDFs, which are then stored in Milvus for efficient semantic search. Users interact with the system through a Streamlit front-end, which communicates with a FastAPI service to query the vector database. The architecture includes components like gRPC for service communication and RabbitMQ for message brokering, enabling a scalable, high-performance document retrieval system.


![image](https://github.com/user-attachments/assets/22e399b0-faf5-452b-8e00-994757ea605f)


![image](https://github.com/user-attachments/assets/69fa4774-2791-43e8-82a7-0bd112de5aff)


