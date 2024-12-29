import os

import pika
import json
from rag_agent import get_answer

# RabbitMQ configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST","localhost")
REQUEST_QUEUE = os.getenv("REQUEST_QUEUE","query_requests")
RESPONSE_QUEUE = os.getenv("RESPONSE_QUEUE","query_responses")
RABBITMQ_USER = os.getenv("RABBITMQ_USER",'admin')  # Replace with your RabbitMQ username
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD",'admin')  # Replace with your RabbitMQ password

class QueueProcessor:
    def __init__(self, input_queue, output_queue, rabbitmq_host=RABBITMQ_HOST):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.rabbitmq_host = rabbitmq_host

        # Publish the query to RabbitMQ
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        # Set up the connection and channel for RabbitMQ using the credentials
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=credentials
        ))
        self.channel = connection.channel()

        # Declare the input and output queues (ensures they exist)
        self.channel.queue_declare(queue=self.input_queue, durable=True)
        self.channel.queue_declare(queue=self.output_queue, durable=True)

    def process_message(self, query_id, query):
        """
        Process the message received from the input queue.
        This function can be customized as needed.
        """
        print(f"Processing query {query_id}: {query}")

        # Example processing step (simply returning the query prefixed with 'Processed:')
        processed_result = get_answer(query)
        # processed_result = f"{query_id} response: rag not connected"

        # Return processed result
        return processed_result

    def publish_to_output(self, query_id, result):
        """
        Publish the processed result along with the query_id to the output queue.
        """
        # Create a message containing both query_id and the result
        message = {
            'query_id': query_id,
            'result': result
        }

        # Publish the message to the output queue
        self.channel.basic_publish(
            exchange='',
            routing_key=self.output_queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2  # Make the message persistent
            )
        )
        print(f"Published result to {self.output_queue}: {message}")

    def callback(self, ch, method, properties, body):
        """
        Callback function to be called when a message is received from the input queue.
        It processes the message and publishes the result to the output queue.
        """
        # Decode the message body
        message = json.loads(body.decode())

        # Extract query_id and query
        query_id = message['query_id']
        query = message['query']

        # Process the received message
        result = self.process_message(query_id, query)

        # Publish the processed result to the output queue
        self.publish_to_output(query_id, result)

        # Acknowledge the message to remove it from the input queue
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_listening(self):
        """
        Start listening to the input queue and process messages as they arrive.
        """
        # Subscribe to the input queue
        self.channel.basic_consume(queue=self.input_queue, on_message_callback=self.callback)

        print(f"Waiting for messages in {self.input_queue}. To exit press CTRL+C")
        self.channel.start_consuming()

    def close_connection(self):
        """
        Close the connection to RabbitMQ.
        """
        self.connection.close()


if __name__ == "__main__":
    # Input and output queue names
    input_queue = 'query_requests'
    output_queue = 'query_responses'

    # Create an instance of QueueProcessor
    processor = QueueProcessor(input_queue=input_queue, output_queue=output_queue)

    try:
        # Start listening for messages
        processor.start_listening()
    except KeyboardInterrupt:
        # Gracefully close the connection on interruption (e.g., CTRL+C)
        print("Interrupted, closing connection...")
    finally:
        # Ensure the connection is properly closed
        processor.close_connection()
