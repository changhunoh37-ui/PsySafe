"""
judge.py
--------
LLM-as-a-Judge 인터페이스. OpenAI / Anthropic 모델을 통일된 방식으로 호출합니다.

지원 모델 예시:
  OpenAI   : gpt-3.5-turbo, gpt-4o-mini, gpt-4o, gpt-4-turbo
  Anthropic: claude-3-5-haiku-20251001, claude-3-5-sonnet-20241022, claude-opus-4-7

API 키 설정:
  OpenAI   : api/OAI_CONFIG_LIST
  Anthropic: api/ANTHROPIC_CONFIG_LIST  (없으면 ANTHROPIC_API_KEY 환경변수)
"""

import json
import os
from openai import OpenAI

SYSTEM_MSG = "You are a helpful assistant."
_ANTHROPIC_CONFIG_PATH = "api/ANTHROPIC_CONFIG_LIST"


def load_anthropic_key() -> str:
    """api/ANTHROPIC_CONFIG_LIST 또는 환경변수에서 Anthropic API 키 로드"""
    if os.path.exists(_ANTHROPIC_CONFIG_PATH):
        with open(_ANTHROPIC_CONFIG_PATH) as f:
            return json.load(f)[0]["api_key"]
    return os.environ.get("ANTHROPIC_API_KEY", "")


def _call_openai(prompt: str, model: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user",   "content": prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content


def _call_anthropic(prompt: str, model: str, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=SYSTEM_MSG,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def run_judge(prompt: str, model: str, openai_key: str = None, anthropic_key: str = None) -> str:
    """
    judge 모델을 호출하여 평가 결과 문자열을 반환합니다.

    Args:
        prompt       : 평가 프롬프트 (eval_gpt_dangerous.txt 포맷)
        model        : 모델 이름 (gpt-* 또는 claude-*)
        openai_key   : OpenAI API 키 (None이면 호출부에서 주입)
        anthropic_key: Anthropic API 키 (None이면 api/ANTHROPIC_CONFIG_LIST 또는 환경변수 사용)
    """
    if "claude" in model.lower():
        key = anthropic_key or load_anthropic_key()
        if not key:
            raise ValueError("Anthropic API 키가 없습니다. api/ANTHROPIC_CONFIG_LIST를 확인하세요.")
        return _call_anthropic(prompt, model, key)
    else:
        if not openai_key:
            raise ValueError(f"OpenAI 모델({model}) 사용 시 openai_key가 필요합니다.")
        return _call_openai(prompt, model, openai_key)


def model_tag(model: str) -> str:
    """모델 이름을 파일 경로용 태그로 변환 (e.g. gpt-4o-mini → gpt_4o_mini)"""
    import re
    return re.sub(r"[^\w]", "_", model)
