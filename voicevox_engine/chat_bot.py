
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain
from langchain import PromptTemplate
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)
import openai
from huggingsound import SpeechRecognitionModel

from transformers import (
    Wav2Vec2Processor, 
    AutoModelForCTC
)
import os

def speech_to_text(model, audio_paths):
    transcriptions = model.transcribe(audio_paths)
    text = ' .'.join(list(t['transcription'] for t in transcriptions)) 
    return text

def ask_bot_api(message):
    chat = ChatOpenAI(openai_api_key=os.getenv("OPENAI_KEY"))
    message = [HumanMessage(content=message)]
    return chat(message)

def speech_to_text_api(audio_file):
    openai.api_key = os.getenv("OPENAI_KEY")
    audio_file = open(audio_file, 'rb')
    transcript = openai.Audio.transcribe("whisper-1", audio_file,"response_format:utf-8", "language:ja")
    text = transcript['text']
    return text

if __name__ == "__main__":
    print(os.getenv("OPENAI_KEY"))
