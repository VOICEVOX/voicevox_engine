
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
from onnxruntime import InferenceSession

def speech_to_text(model, audio_paths):
    transcriptions = model.transcribe(audio_paths)
    text = ' .'.join(list(t['transcription'] for t in transcriptions)) 
    return text

def ask_bot_api(message):
    chat = ChatOpenAI(openai_api_key="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")
    message = [HumanMessage(content=message)]
    return chat(message)

def speech_to_text_api(audio_file):
    openai.api_key = "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"
    audio_file = open(audio_file, 'rb')
    transcript = openai.Audio.transcribe("whisper-1", audio_file,"response_format:utf-8", "language:ja")
    text = transcript['text']
    return text

if __name__ == "__main__":
    # print(ask_bot_api('hello').content)

    default_model = "jonatasgrosman/wav2vec2-large-xlsr-53-japanese"

    model = SpeechRecognitionModel(default_model)

    audio_paths = "./response.wav"
    transcriptions = model.transcribe([audio_paths])