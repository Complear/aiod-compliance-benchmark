# Reader component: Ministral-3-3B-Instruct-2512 (Apache 2.0) served by llama.cpp.
# Pin LLAMA_IMAGE to a digest when publishing.
ARG LLAMA_IMAGE=ghcr.io/ggml-org/llama.cpp:server
FROM ${LLAMA_IMAGE}
COPY models/Ministral-3-3B-Instruct-2512-Q4_K_M.gguf /models/model.gguf
EXPOSE 8080
CMD ["-m", "/models/model.gguf", "--alias", "ministral-3-3b", "-c", "8192", "--host", "0.0.0.0", "--port", "8080", "--jinja"]
