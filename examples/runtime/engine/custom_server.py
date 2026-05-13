import os

from sanic import Sanic, text
from sanic.response import json

import sglang as sgl

engine = None

# Create an instance of the Sanic app
app = Sanic("sanic-server")


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


# Define an asynchronous route handler
@app.route("/generate", methods=["POST"])
async def generate(request):
    prompt = request.json.get("prompt")
    if not prompt:
        return json({"error": "Prompt is required"}, status=400)

    # async_generate returns a dict
    result = await engine.async_generate(prompt)

    return text(result["text"])


@app.route("/generate_stream", methods=["POST"])
async def generate_stream(request):
    prompt = request.json.get("prompt")

    if not prompt:
        return json({"error": "Prompt is required"}, status=400)

    # async_generate returns a dict
    result = await engine.async_generate(prompt, stream=True)

    # https://sanic.dev/en/guide/advanced/streaming.md#streaming
    # init the response
    response = await request.respond()

    # result is an async generator
    async for chunk in result:
        await response.send(chunk["text"])

    await response.eof()


def run_server():
    global engine
    engine = sgl.Engine(**build_engine_kwargs())
    app.run(host="0.0.0.0", port=8000, single_process=True)


if __name__ == "__main__":
    run_server()
