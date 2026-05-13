"""
Usage:
python3 local_example_complete.py

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
def few_shot_qa(s, question):
    s += """The following are questions with answers.
Q: What is the capital of France?
A: Paris
Q: What is the capital of Germany?
A: Berlin
Q: What is the capital of Italy?
A: Rome
"""
    s += "Q: " + question + "\n"
    s += "A:" + sgl.gen("answer", stop="\n", temperature=0)


def single():
    state = few_shot_qa.run(
        question="What is the capital of the United States?")
    answer = state["answer"].strip().lower()

    if os.getenv("SGLANG_EXAMPLE_LOAD_FORMAT") == "dummy":
        assert answer, "answer should not be empty"
    else:
        assert "washington" in answer, f"answer: {state['answer']}"

    print(state.text())


def stream():
    state = few_shot_qa.run(
        question="What is the capital of the United States?", stream=True
    )

    for out in state.text_iter("answer"):
        print(out, end="", flush=True)
    print()


def batch():
    states = few_shot_qa.run_batch(
        [
            {"question": "What is the capital of the United States?"},
            {"question": "What is the capital of China?"},
        ]
    )

    for s in states:
        print(s["answer"])


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
