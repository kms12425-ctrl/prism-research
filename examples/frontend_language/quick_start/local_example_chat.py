"""
Usage:
python3 local_example_chat.py

Optional environment variables:
- SGLANG_EXAMPLE_MODEL
- SGLANG_EXAMPLE_LOAD_FORMAT
"""

import os

import sglang as sgl


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


@sgl.function
def multi_turn_question(s, question_1, question_2):
    s += sgl.user(question_1)
    s += sgl.assistant(sgl.gen("answer_1", max_tokens=256))
    s += sgl.user(question_2)
    s += sgl.assistant(sgl.gen("answer_2", max_tokens=256))


def single():
    state = multi_turn_question.run(
        question_1="What is the capital of the United States?",
        question_2="List two local attractions.",
    )

    for m in state.messages():
        print(m["role"], ":", m["content"])

    print("\n-- answer_1 --\n", state["answer_1"])


def stream():
    state = multi_turn_question.run(
        question_1="What is the capital of the United States?",
        question_2="List two local attractions.",
        stream=True,
    )

    for out in state.text_iter():
        print(out, end="", flush=True)
    print()


def batch():
    states = multi_turn_question.run_batch(
        [
            {
                "question_1": "What is the capital of the United States?",
                "question_2": "List two local attractions.",
            },
            {
                "question_1": "What is the capital of France?",
                "question_2": "What is the population of this city?",
            },
        ]
    )

    for s in states:
        print(s.messages())


if __name__ == "__main__":
    runtime = sgl.Runtime(**build_runtime_kwargs())
    sgl.set_default_backend(runtime)

    # Run a single request
    print("\n========== single ==========\n")
    single()

    # Stream output
    print("\n========== stream ==========\n")
    stream()

    # Run a batch of requests
    print("\n========== batch ==========\n")
    batch()

    runtime.shutdown()
