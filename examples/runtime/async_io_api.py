"""
Usage:

python3 async_io.py

Optional environment variables:
- SGLANG_EXAMPLE_MODEL
- SGLANG_EXAMPLE_LOAD_FORMAT
"""

import asyncio
import os

from sglang import Runtime


def build_runtime_kwargs():
    runtime_kwargs = {
        "model_path": os.getenv(
            "SGLANG_EXAMPLE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"
        ),
        "disable_cuda_graph": os.getenv(
            "SGLANG_EXAMPLE_DISABLE_CUDA_GRAPH", "1"
        ).lower()
        not in {"0", "false", "no"},
    }
    load_format = os.getenv("SGLANG_EXAMPLE_LOAD_FORMAT")
    if load_format:
        runtime_kwargs["load_format"] = load_format
    mem_fraction_static = os.getenv("SGLANG_EXAMPLE_MEM_FRACTION_STATIC")
    if mem_fraction_static:
        runtime_kwargs["mem_fraction_static"] = float(mem_fraction_static)
    return runtime_kwargs


async def generate(
    engine,
    prompt,
    sampling_params,
):
    tokenizer = engine.get_tokenizer()

    messages = [
        {
            "role": "system",
            "content": "You will be given question answer tasks.",
        },
        {"role": "user", "content": prompt},
    ]

    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    stream = engine.add_request(prompt, sampling_params)

    async for output in stream:
        print(output, end="", flush=True)
    print()


if __name__ == "__main__":
    runtime = Runtime(**build_runtime_kwargs())
    print("--- runtime ready ---\n")

    prompt = "Who is Alan Turing?"
    sampling_params = {"max_new_tokens": 128}
    asyncio.run(generate(runtime, prompt, sampling_params))

    runtime.shutdown()
