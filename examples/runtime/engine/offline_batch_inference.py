import os

import sglang as sgl


def build_engine_kwargs():
    engine_kwargs = {
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
        engine_kwargs["load_format"] = load_format
    mem_fraction_static = os.getenv("SGLANG_EXAMPLE_MEM_FRACTION_STATIC")
    if mem_fraction_static:
        engine_kwargs["mem_fraction_static"] = float(mem_fraction_static)
    return engine_kwargs


def main():
    # Sample prompts.
    prompts = [
        "Hello, my name is",
        "The president of the United States is",
        "The capital of France is",
        "The future of AI is",
    ]
    # Create a sampling params object.
    sampling_params = {"temperature": 0.8, "top_p": 0.95}

    # Create an LLM.
    llm = sgl.Engine(**build_engine_kwargs())

    outputs = llm.generate(prompts, sampling_params)
    # Print the outputs.
    for prompt, output in zip(prompts, outputs):
        print("===============================")
        print(f"Prompt: {prompt}\nGenerated text: {output['text']}")


# The __main__ condition is necessary here because we use "spawn" to create subprocesses
# Spawn starts a fresh program every time, if there is no __main__, it will run into infinite loop to keep spawning processes from sgl.Engine
if __name__ == "__main__":
    main()
