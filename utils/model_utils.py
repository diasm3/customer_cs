# utils/model_utils.py
import asyncio
import torch
from typing import Literal
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from langchain_ollama.llms import OllamaLLM
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

MODEL_TYPE = Literal["solar", "qwen3", "ollama"]

# 전역 모델 변수
tokenizer = None
model = None
qwen3_tokenizer = None
qwen3_model = None

def load_solar_model():
    global tokenizer, model
    try:
        if tokenizer is not None and model is not None:
            return
            
        tokenizer = AutoTokenizer.from_pretrained("Upstage/SOLAR-10.7B-Instruct-v1.0")
        model = AutoModelForCausalLM.from_pretrained(
            "Upstage/SOLAR-10.7B-Instruct-v1.0",
            device_map="auto",
            torch_dtype=torch.float16,
        )
        print("SOLAR 모델 로딩 완료!")
    except Exception as e:
        print(f"SOLAR 모델 로딩 중 오류 발생: {str(e)}")
        raise

def load_qwen3_model():
    global qwen3_tokenizer, qwen3_model
    try:
        if qwen3_tokenizer is not None and qwen3_model is not None:
            return
            
        base_model = "Qwen/Qwen3-4B"
        output_dir = "./models/skt_persona_qwen3_final"
        
        qwen3_tokenizer = AutoTokenizer.from_pretrained(output_dir, trust_remote_code=True)
        
        base_model_instance = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        
        qwen3_model = PeftModel.from_pretrained(base_model_instance, output_dir)
        qwen3_model.eval()
        
        print("Qwen3 모델 로딩 완료!")
    except Exception as e:
        print(f"Qwen3 모델 로딩 중 오류 발생: {str(e)}")
        raise

async def generate_solar_response(messages, temperature=0.2, max_length=4096):
    try:
        if tokenizer is None or model is None:
            await asyncio.to_thread(load_solar_model)
        
        conversation = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                conversation.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                conversation.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                conversation.append({"role": "assistant", "content": msg.content})
            elif getattr(msg, 'role', None) == 'tool':
                conversation.append({"role": "user", "content": f"도구 응답: {msg.content}"})
        
        prompt = await asyncio.to_thread(
            lambda: tokenizer.apply_chat_template(conversation, tokenize=False, add_generation_prompt=True)
        )
        
        inputs = await asyncio.to_thread(
            lambda: tokenizer(prompt, return_tensors="pt").to(model.device)
        )
        
        generation_kwargs = {
            "do_sample": True,
            "temperature": temperature,
            "max_length": max_length,
            "repetition_penalty": 1.1,
            "top_p": 0.95
        }
        
        outputs = await asyncio.to_thread(
            lambda: model.generate(**inputs, **generation_kwargs)
        )
        
        output_text = await asyncio.to_thread(
            lambda: tokenizer.decode(outputs[0], skip_special_tokens=True)
        )
        
        response_only = output_text[len(prompt):].strip()
        print(f"SOLAR 생성 결과: {response_only}")
        return response_only
        
    except Exception as e:
        print(f"SOLAR 응답 생성 중 오류 발생: {str(e)}")
        return f"죄송합니다, 응답을 생성하는 중에 오류가 발생했습니다: {str(e)}"

async def generate_qwen3_response(messages, temperature=0.2, max_length=4096):
    try:
        if qwen3_tokenizer is None or qwen3_model is None:
            await asyncio.to_thread(load_qwen3_model)
        
        conversation = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                conversation.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                conversation.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                conversation.append({"role": "assistant", "content": msg.content})
            elif getattr(msg, 'role', None) == 'tool':
                conversation.append({"role": "user", "content": f"도구 응답: {msg.content}"})
        
        prompt = await asyncio.to_thread(
            lambda: qwen3_tokenizer.apply_chat_template(conversation, tokenize=False, add_generation_prompt=True)
        )
        
        inputs = await asyncio.to_thread(
            lambda: qwen3_tokenizer(prompt, return_tensors="pt").to(qwen3_model.device)
        )
        
        generation_kwargs = {
            "do_sample": True,
            "temperature": temperature,
            "max_length": max_length,
            "repetition_penalty": 1.1,
            "top_p": 0.95
        }
        
        outputs = await asyncio.to_thread(
            lambda: qwen3_model.generate(**inputs, **generation_kwargs)
        )
        
        output_text = await asyncio.to_thread(
            lambda: qwen3_tokenizer.decode(outputs[0], skip_special_tokens=True)
        )
        
        response_only = output_text[len(prompt):].strip()
        print(f"Qwen3 생성 결과: {response_only}")
        return response_only
        
    except Exception as e:
        print(f"Qwen3 응답 생성 중 오류 발생: {str(e)}")
        return f"죄송합니다, 응답을 생성하는 중에 오류가 발생했습니다: {str(e)}"

async def generate_ollama_response(messages, model_name="gemma3:4b", temperature=0.7, max_length=4096):
    try:
        client = OllamaLLM(
            model=model_name,
            temperature=temperature,
        )
        
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                formatted_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                formatted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_messages.append({"role": "assistant", "content": msg.content})
            elif getattr(msg, 'role', None) == 'tool':
                formatted_messages.append({"role": "user", "content": f"도구 응답: {msg.content}"})
        
        prompt_text = ""
        for msg in formatted_messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt_text += f"시스템: {content}\n\n"
            elif role == "user":
                prompt_text += f"사용자: {content}\n\n"
            elif role == "assistant":
                prompt_text += f"어시스턴트: {content}\n\n"
        
        prompt_text += "어시스턴트: "
        
        response = await asyncio.to_thread(
            lambda: client.invoke(prompt_text)
        )
        
        print(f"Ollama ({model_name}) 생성 결과: {response}")
        return response
        
    except Exception as e:
        print(f"Ollama 응답 생성 중 오류 발생: {str(e)}")
        return f"죄송합니다, Ollama 응답을 생성하는 중에 오류가 발생했습니다: {str(e)}"

async def generate_model_response(messages, model_type: MODEL_TYPE = "qwen3", temperature=0.2, max_length=4096, ollama_model_name=None):
    """통합 모델 응답 생성 함수"""
    if model_type == "solar":
        return await generate_solar_response(messages, temperature, max_length)
    elif model_type == "qwen3":
        return await generate_qwen3_response(messages, temperature, max_length)
    elif model_type == "ollama":
        model_name = ollama_model_name or "gemma3:4b"
        return await generate_ollama_response(messages, model_name, temperature, max_length)
    else:
        raise ValueError(f"지원되지 않는 모델 타입입니다: {model_type}")