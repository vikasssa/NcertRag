import time
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_milvus import Milvus
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, StateGraph
from langchain_core.documents import Document
from typing_extensions import List, TypedDict
from langchain_core.messages import HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field


class Lang(BaseModel):
    language: str = Field(description="The language in question is asked")

#llm settings settings
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-8b")
smart_llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
structured_llm = smart_llm.with_structured_output(Lang)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
vector_store = Milvus(embedding_function=embeddings,auto_id=True)


# Define state for application
class State(TypedDict):
    question: str
    translated_question: str
    context: List[Document]
    language: str
    answer: str


def language_interpreter(state: State):
    sys_msg = ('You are an experienced language_interpreter tasked with identifying the language of statement.'
                'Examples:'
               '--- statement 1:हेरीडिटी इसे कहते हैं '
               '--- language:Hindi'
               '--- statement 2: What is Heredity'
               '--- language: English')
    human_msg = f"So what is language of following statement: {state["question"]}"
    response = structured_llm.invoke(sys_msg + human_msg)
    return {"language": response.language}


def query_translator(state: State):
    sys_msg = ('You are an experienced hindi to english translator tasked with translating hindi '
               'question to english question.'
               'if question is already in english then do not do anything '
               'and return original question in response '
               'Your response must contain only question.')
    human_msg = f"language: {state['language']} question: {state["question"]}"
    response = llm.invoke(sys_msg + human_msg)
    return {"translated_question": response.content}


# Define application steps
def retrieve(state: State):
    retrieved_docs = vector_store.similarity_search(state["translated_question"])
    return {"context": retrieved_docs}


def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    sys_msg = ('You are a helpful assistant tasked with generating response for the '
                                    'given question and context.You will ensure that response is '
                                    'based out of context only.'
                                    'In case question cannot be answered from given context '
                                    'then respond with "question cannot be answered."')
    response = llm.invoke(sys_msg+"\n\nquestion:"+state["question"]+"\n\ncontext:"+docs_content+"\n\nlanguage:"+state["language"] )
    return {"answer": response.content}

graph_builder = StateGraph(State).add_sequence([language_interpreter,query_translator,retrieve, generate])

graph_builder.add_edge(START, "language_interpreter")
graph = graph_builder.compile()

def get_answer(question):
    result = graph.invoke({"question": question})
    return result["answer"]

if __name__ == "__main__":
    for msg, metadata in graph.stream({"question": "हेरीडिटी इसे कहते हैं"}, stream_mode="messages"):
        if (
                msg.content
                and not isinstance(msg, HumanMessage)
                and metadata["langgraph_node"] == "response_translator"
        ):
            print(msg.content, end="|", flush=True)