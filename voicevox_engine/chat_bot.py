
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain, OpenAI
from langchain import PromptTemplate, ConversationChain
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain.memory import ConversationBufferMemory
import openai
from huggingsound import SpeechRecognitionModel
from transformers import (
    Wav2Vec2Processor, 
    AutoModelForCTC
)
from typing import List, Dict
import os

llm = OpenAI(
    temperature=0,
    openai_api_key=os.getenv("OPENAI_KEY"),
    model_name='text-davinci-003',
     # can be used with llms like 'gpt-3.5-turbo'
)

def speech_to_text(model, audio_paths):
    transcriptions = model.transcribe(audio_paths)
    text = ' .'.join(list(t['transcription'] for t in transcriptions)) 
    return text

def ask_bot_api(message, history=None):
    memory = ConversationBufferMemory(return_messages=False)
    if history is not None:
        for mes in history:
            memory.chat_memory.add_user_message(mes.request)
            memory.chat_memory.add_ai_message(mes.response)
    conversation_buf = ConversationChain(
        llm = llm,
        memory=memory
    )
    reponse = conversation_buf.run(message)
    return reponse

def speech_to_text_api(audio_file):
    openai.api_key = os.getenv("OPENAI_KEY")
    audio_file = open(audio_file, 'rb')
    transcript = openai.Audio.transcribe("whisper-1", audio_file,"response_format:utf-8", "language:ja")
    text = transcript['text']
    return text

if __name__ == "__main__":
    print(os.getenv("OPENAI_KEY"))


