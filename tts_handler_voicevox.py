from collections import deque
from dataclasses import dataclass, field
from torch.multiprocessing import Manager
import os
import queue
import re
import threading
import time
from typing import Dict, Optional, cast
import uuid
import numpy as np
from loguru import logger
from pydantic import BaseModel, Field
from abc import ABC
import wave
import io
import requests
import json

from chat_engine.contexts.handler_context import HandlerContext
from chat_engine.data_models.chat_engine_config_data import ChatEngineConfigModel, HandlerBaseConfigModel
from chat_engine.common.handler_base import HandlerBase, HandlerBaseInfo, HandlerDataInfo, HandlerDetail
from chat_engine.data_models.chat_data.chat_data_model import ChatData
from chat_engine.common.chat_data_type import ChatDataType
from chat_engine.contexts.session_context import SessionContext
from chat_engine.data_models.runtime_data.data_bundle import DataBundle, DataBundleDefinition, DataBundleEntry
from utils.directory_info import DirectoryInfo
from pathlib import Path
from .voicevox_processing import VoiceVoxProcessor


class TTSConfig(HandlerBaseConfigModel, BaseModel):
    api_url: str = Field(default=None)
    spk_id: int = Field(default=1)
    sample_rate: int = Field(default=24000)
    voicelib_dir: str = Field()
    runtime_dir: str = Field()
    use_gpu: bool = Field(default=False)
    cpu_num_threads: int = Field(default=None)
    load_all_models: bool = Field(default=None)


@dataclass
class HandlerTask:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    result_queue: queue.Queue = field(default_factory=queue.Queue)
    speech_id: str = field(default=None)
    speech_end: bool = field(default=False)


class TTSContext(HandlerContext):
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.config = None
        self.input_text = ''
        self.task_queue: deque[Optional[HandlerTask]] = deque()  # <- sửa ở đây
        self.condition = threading.Condition()


class HandlerTTS(HandlerBase, ABC):
    def __init__(self):
        super().__init__()
        self.api_url = None
        self.spk_id = None
        self.sample_rate = None
        self.task_queue_map = {}

    def get_handler_info(self) -> HandlerBaseInfo:
        return HandlerBaseInfo(config_model=TTSConfig)

    def get_handler_detail(self, session_context: SessionContext,
                           context: HandlerContext) -> HandlerDetail:
        definition = DataBundleDefinition()
        definition.add_entry(DataBundleEntry.create_audio_entry("avatar_audio", 1, self.sample_rate))
        inputs = {ChatDataType.AVATAR_TEXT: HandlerDataInfo(type=ChatDataType.AVATAR_TEXT)}
        outputs = {ChatDataType.AVATAR_AUDIO: HandlerDataInfo(type=ChatDataType.AVATAR_AUDIO, definition=definition)}
        return HandlerDetail(inputs=inputs, outputs=outputs)

    # def load(self, engine_config: ChatEngineConfigModel, handler_config: Optional[BaseModel] = None):
    #     if isinstance(handler_config, TTSConfig):
    #         self.api_url = handler_config.api_url
    #         self.spk_id = handler_config.spk_id
    #         self.sample_rate = handler_config.sample_rate
    def load(self, engine_config: ChatEngineConfigModel, handler_config: Optional[BaseModel] = None):
        if isinstance(handler_config, TTSConfig):
            # Thiết lập processor
            self.processor = VoiceVoxProcessor(
                voicelib_dirs=[Path(handler_config.voicelib_dir)],
                runtime_dirs=[Path(handler_config.runtime_dir)],
                use_gpu=handler_config.use_gpu,
                cpu_num_threads=handler_config.cpu_num_threads,
                load_all_models=handler_config.load_all_models,
                sample_rate= handler_config.sample_rate
            )
            self.spk_id = handler_config.spk_id
            self.sample_rate = handler_config.sample_rate

    def create_context(self, session_context, handler_config=None):
        return TTSContext(session_context.session_info.session_id)

    def start_context(self, session_context, context: HandlerContext):
        context = cast(TTSContext, context)
        output_def = self.get_handler_detail(session_context, context).outputs[ChatDataType.AVATAR_AUDIO].definition

        def task_consumer(task_queue: deque[Optional[HandlerTask]], condition: threading.Condition, callback):
            while True:
                with condition:
                    while not task_queue:
                        condition.wait()
                    task = task_queue.popleft()
                if task is None:  # <- kiểm tra trước khi cast
                    break
                try:
                    task = cast(HandlerTask, task)
                    while True:
                        try:
                            audio = task.result_queue.get(timeout=1)
                        except queue.Empty:
                            continue
                        if audio is None:
                            break
                        output = DataBundle(output_def)
                        output.set_main_data(audio)
                        output.add_meta("avatar_speech_end", task.speech_end)
                        output.add_meta("speech_id", task.speech_id)
                        callback(output)
                except Exception as e:
                    logger.error(f"Error in task_consumer: {e}")

        thread = threading.Thread(
            target=task_consumer,
            args=(context.task_queue, context.condition, context.submit_data),
            daemon=True
        )
        thread.start()
        context.task_consume_thread = thread
        self.task_queue_map[context.session_id] = context.task_queue

    def _call_voicevox(self, text: str) -> np.ndarray:
        try:
            resp_q = requests.post(
                f"{self.api_url}/audio_query",
                params={"text": text, "speaker": self.spk_id}
            )
            resp_q.raise_for_status()
            query = resp_q.json()

            resp_w = requests.post(
                f"{self.api_url}/synthesis",
                params={"speaker": self.spk_id},
                headers={"Content-Type": "application/json"},
                data=json.dumps(query),
            )
            resp_w.raise_for_status()

            wav_bytes = resp_w.content
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            return samples[np.newaxis, :]
        except Exception as e:
            logger.exception(f"TTS API call failed for text='{text}': {e}")
            return np.zeros((1, self.sample_rate), dtype=np.float32)

    def filter_text(self, text: str) -> str:
        pattern = r"[^a-zA-Z0-9\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff,\.\~!?，。！？ ]"
        return re.sub(pattern, "", text)

    def handle(self, context: HandlerContext, inputs: ChatData,
               output_defs: Dict[ChatDataType, HandlerDataInfo]):
        context = cast(TTSContext, context)
        if inputs.type != ChatDataType.AVATAR_TEXT:
            return

        text = inputs.data.get_main_data() or ''
        speech_id = inputs.data.get_meta("speech_id") or context.session_id
        text_end = inputs.data.get_meta("avatar_text_end", False)

        context.input_text += self.filter_text(text)

        def enqueue_sentence(sentence: str, end_flag: bool = False):
            task = HandlerTask(speech_id=speech_id, speech_end=end_flag)
            # Thay: gọi trực tiếp vào VoiceVoxProcessor
            audio = self.processor.synthesize(sentence, self.spk_id)
            task.result_queue.put(audio)
            task.result_queue.put(None)
            with context.condition:
                context.task_queue.append(task)
                context.condition.notify()

        if not text_end:
            parts = re.split(r'(?<=[,.~!?，。！？])', context.input_text)
            if len(parts) > 1:
                complete, rest = parts[:-1], parts[-1]
                context.input_text = rest
                for s in complete:
                    if s.strip():
                        enqueue_sentence(s)
        else:
            if context.input_text.strip():
                enqueue_sentence(context.input_text.strip(), end_flag=True)
                context.input_text = ''
            # kết thúc hẳn
            end_task = HandlerTask(speech_id=speech_id, speech_end=True)
            end_task.result_queue.put(np.zeros((1, self.sample_rate), dtype=np.float32))
            end_task.result_queue.put(None)
            with context.condition:
                context.task_queue.append(end_task)
                context.condition.notify()

    def destroy_context(self, context: HandlerContext):
        context = cast(TTSContext, context)
        with context.condition:
            context.task_queue.append(None)
            context.condition.notify()
        self.task_queue_map.pop(context.session_id, None)
