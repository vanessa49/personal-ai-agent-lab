# judge/llm_judge.py
import requests
import json
import time
import re
from config import (
    JUDGE_BACKEND,
    POLLINATIONS_API_KEY, POLLINATIONS_BASE_URL, POLLINATIONS_MODEL,
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    JUDGE_DELAY_SECONDS, JUDGE_MAX_TOKENS
)

# ============================================================
# Judge Prompt
# 针对"认知轨迹学习"这个目标设计，不是通用QA评估
# ============================================================

JUDGE_PROMPT_TEMPLATE = """You are evaluating two AI responses to see which one better reflects iterative, trajectory-based thinking — as opposed to simple Q&A answering.

The context for this evaluation:
- We are testing whether a fine-tuned model has learned to reason iteratively, 
  like how a researcher actually thinks through problems, rather than just retrieving answers.
- The ideal response explores the problem space, revises assumptions, and shows the PROCESS of thinking.

---

QUESTION TYPE: {category}
{context_section}
USER INPUT: {question}

RESPONSE A:
{response_a}

RESPONSE B:
{response_b}

---

Please score EACH response on these 4 dimensions (1-5 scale):

1. **Iterative Reasoning** (1=direct answer, 5=explores multiple angles before concluding)
2. **Correction Willingness** (1=never revises, 5=naturally revises assumptions when needed)  
3. **Trajectory Sense** (1=isolated answer, 5=feels like part of an ongoing reasoning process)
4. **Coherence** (1=incoherent, 5=logically sound and well-structured)

IMPORTANT: Return ONLY valid JSON, no other text, no markdown.

{{
  "response_a": {{
    "iterative_reasoning": <1-5>,
    "correction_willingness": <1-5>,
    "trajectory_sense": <1-5>,
    "coherence": <1-5>,
    "brief_reason": "<one sentence explaining the scores>"
  }},
  "response_b": {{
    "iterative_reasoning": <1-5>,
    "correction_willingness": <1-5>,
    "trajectory_sense": <1-5>,
    "coherence": <1-5>,
    "brief_reason": "<one sentence explaining the scores>"
  }},
  "overall_winner": "A" or "B" or "tie"
}}"""


def _build_prompt(question: str, response_a: str, response_b: str,
                  category: str, context: list = None) -> str:
    """构建judge prompt"""
    if context:
        ctx_lines = "\n".join(
            [f"  {m['role'].upper()}: {m['content']}" for m in context]
        )
        context_section = f"PRIOR CONTEXT:\n{ctx_lines}\n"
    else:
        context_section = ""

    return JUDGE_PROMPT_TEMPLATE.format(
        category=category.upper(),
        context_section=context_section,
        question=question,
        response_a=response_a,
        response_b=response_b
    )


def _call_api(prompt: str, backend: str) -> str:
    """调用API，返回原始文本"""
    if backend == "pollinations":
        headers = {"Content-Type": "application/json"}
        if POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"

        payload = {
            "model": POLLINATIONS_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": JUDGE_MAX_TOKENS,
            "temperature": 0.1   # judge要稳定，温度低
        }
        r = requests.post(
            f"{POLLINATIONS_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    elif backend == "deepseek":
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": JUDGE_MAX_TOKENS,
            "temperature": 0.1
        }
        r = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    else:
        raise ValueError(f"Unknown backend: {backend}")


def _parse_json_response(raw: str) -> dict:
    """从模型输出中提取JSON，处理各种格式问题"""
    # 去掉markdown代码块
    cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip()
    cleaned = cleaned.replace('```', '').strip()

    # 尝试直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 尝试找到第一个完整的JSON对象
    try:
        start = cleaned.index('{')
        # 找匹配的结束括号
        depth = 0
        for i, ch in enumerate(cleaned[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return json.loads(cleaned[start:i+1])
    except (ValueError, json.JSONDecodeError):
        pass

    return None


def judge(question: str, response_base: str, response_ft: str,
          category: str, context: list = None,
          backend: str = None) -> dict:
    """
    调用LLM judge对两个回答进行评分。
    
    Args:
        question: 测试问题
        response_base: baseline模型的回答
        response_ft: fine-tuned模型的回答
        category: 测试类别 ("style"/"trajectory"/"correction")
        context: 多轮对话历史（trajectory测试用）
        backend: 覆盖config中的默认backend
    
    Returns:
        包含评分的dict，失败时返回None
    """
    active_backend = backend or JUDGE_BACKEND
    prompt = _build_prompt(question, response_base, response_ft,
                           category, context)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            raw = _call_api(prompt, active_backend)
            parsed = _parse_json_response(raw)

            if parsed:
                time.sleep(JUDGE_DELAY_SECONDS)
                return {
                    "scores": parsed,
                    "backend": active_backend,
                    "model": POLLINATIONS_MODEL if active_backend == "pollinations" else DEEPSEEK_MODEL,
                    "raw_response": raw
                }
            else:
                print(f"  ⚠️  JSON解析失败 (attempt {attempt+1}), raw: {raw[:100]}...")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"  ⚠️  Rate limit，等待{wait}秒...")
                time.sleep(wait)
            else:
                print(f"  ❌ HTTP错误: {e}")
                break
        except Exception as e:
            print(f"  ❌ Judge调用失败 (attempt {attempt+1}): {e}")
            time.sleep(5)

    # 如果主backend失败，自动切换
    if active_backend == "pollinations" and DEEPSEEK_API_KEY:
        print(f"  🔄 Pollinations失败，切换到DeepSeek...")
        return judge(question, response_base, response_ft,
                     category, context, backend="deepseek")

    return None
