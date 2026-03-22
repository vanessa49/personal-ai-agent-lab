import json
import sys
from datetime import datetime

def generate_sample(instruction, input_text, reasoning, output, score, source="self"):
    return {
        "instruction": instruction,
        "input": input_text,
        "reasoning": reasoning,
        "output": output,
        "score": score,
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "source": source
    }