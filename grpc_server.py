import os
import time
import grpc
import uuid
import threading
from concurrent import futures
import query_service_pb2
import query_service_pb2_grpc
import pika
import json
from collections import defaultdict
import re
from urllib.parse import unquote



# RabbitMQ configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST","localhost")
REQUEST_QUEUE = os.getenv("REQUEST_QUEUE","query_requests")
RESPONSE_QUEUE = os.getenv("RESPONSE_QUEUE","query_responses")
RABBITMQ_USER = os.getenv("RABBITMQ_USER",'admin')  # Replace with your RabbitMQ username
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD",'admin')  # Replace with your RabbitMQ password

# In-memory store to match query_id and responses
response_store = {}
client_lookup = defaultdict(list)


def extract_ip(address):
    # Decode URL-encoded parts like %5B and %5D
    decoded_address = unquote(address)

    # Regular expression to extract IPv6 or IPv4 address
    match = re.search(r'\[([^\]]+)\]', decoded_address)  # For IPv6
    if match:
        return match.group(1)
    match = re.search(r'ipv4:(\d+\.\d+\.\d+\.\d+)', decoded_address)  # For IPv4
    if match:
        return match.group(1)
    return None  # Return None if no IP found

class QueryService(query_service_pb2_grpc.QueryServiceServicer):
    def SubmitQuery(self, request, context):
        # Generate a unique query ID
        query_id = str(uuid.uuid4())
        print(f"query_id {query_id}")
        #save queryid and client mapping
        client_id = context.peer()
        client_lookup[client_id].append(query_id)
        # Publish the query to RabbitMQ
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=credentials
        ))
        channel = connection.channel()

        # Declare the request queue
        channel.queue_declare(queue=REQUEST_QUEUE, durable=True)

        # Publish the query with query_id
        message = {"query_id": query_id, "query": request.query}
        channel.basic_publish(
            exchange="",
            routing_key=REQUEST_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()

        # Return the query_id to the client
        return query_service_pb2.QueryResponse(query_id=query_id)

    def GetQueryResponse(self, request, context):
        client_id = context.peer()
        # Stream responses from RabbitMQ
        while True:
            query_ids = client_lookup[client_id]
            for query_id in query_ids:
                if query_id in response_store:
                    response = response_store.pop(query_id)
                    client_lookup[client_id].remove(query_id)
                    print(f"query_id {query_id} response {response}")
                    yield query_service_pb2.QueryResult(query_id=query_id, result=response)

def consume_responses():
    # Consume messages from the RabbitMQ response queue
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials
    ))
    channel = connection.channel()

    # Declare the response queue
    channel.queue_declare(queue=RESPONSE_QUEUE, durable=True)

    def callback(ch, method, properties, body):
        message = json.loads(body)
        query_id = message["query_id"]
        result = message["result"]
        response_store[query_id] = result
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=RESPONSE_QUEUE, on_message_callback=callback)
    print("Listening for responses on RabbitMQ...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Shutting down consumer...")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    query_service_pb2_grpc.add_QueryServiceServicer_to_server(QueryService(), server)
    server.add_insecure_port("[::]:50051")
    print("gRPC server started on port 50051")

    # Start RabbitMQ consumer in a separate thread
    consumer_thread = threading.Thread(target=consume_responses, daemon=True)
    consumer_thread.start()

    # Start the gRPC server and block until it's terminated
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
