import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import grpc
import query_service_pb2
import query_service_pb2_grpc
from typing import List, Dict
import threading
from google.protobuf.empty_pb2 import Empty

# Initialize the FastAPI app
app = FastAPI()

GRPC_HOST = os.getenv("GRPC_HOST","localhost:50051")
# gRPC stub and channel (initialized once)
grpc_channel = grpc.insecure_channel(GRPC_HOST)  # Replace with your server's address
grpc_stub = query_service_pb2_grpc.QueryServiceStub(grpc_channel)

# In-memory storage for responses
response_storage : Dict[str,str] = {}
question_mapping: Dict[str, str] = {}

class QueryRequest(BaseModel):
    query: str

@app.post("/submit-query")
async def submit_query(request: QueryRequest):
    """
    Endpoint to submit a query to the gRPC service.
    Returns the `query_id` associated with the submitted query.
    """
    try:
        grpc_request = query_service_pb2.QueryRequest(query=request.query)
        grpc_response = grpc_stub.SubmitQuery(grpc_request)
        query_id = grpc_response.query_id
        question_mapping[query_id]= request.query
        print(f"query id {query_id}")
        # Initialize storage for this query_id
        return query_id
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC Error: {e.details()}")

@app.get("/get-response")
async def get_response():
    """
    Endpoint to retrieve responses.
    """
    if not response_storage:
        raise HTTPException(status_code=404, detail="no response")

    try:
        result = {}
        for key, response in response_storage.items():
            result[question_mapping[key]]=response
        return result
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC Error: {e.details()}")

def background_task():
    responses = grpc_stub.GetQueryResponse(Empty())
    for response in responses:
        # Append new responses to the in-memory storage
        print(response_storage)
        response_storage[response.query_id]=response.result


@app.on_event("startup")
async def on_startup():
    """
    FastAPI startup event.
    Initializes background thread manager for handling query threads.
    """
    thread_manager = threading.Thread(target=background_task, daemon=True)
    thread_manager.start()