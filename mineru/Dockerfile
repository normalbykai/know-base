# 基于 MinerU 3.4.5 官方 docker/global/Dockerfile；镜像名称固定在 Compose 中。
# 若宿主机驱动仅支持 CUDA 12.9，请按 MinerU 官方文档将基础镜像切换为 -cu129 变体。
FROM vllm/vllm-openai:v0.21.0

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-noto-core \
        fonts-noto-cjk \
        fontconfig \
        libgl1 && \
    fc-cache -fv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 固定 MinerU 版本，防止未来的上游接口或模型行为无提示改变。
RUN python3 -m pip install --no-cache-dir 'mineru[core]==3.4.5' --break-system-packages && \
    mineru-models-download -s huggingface -m all

# 官方镜像通过此入口确保 API 使用镜像内已下载的本地模型。
ENTRYPOINT ["/bin/bash", "-c", "export MINERU_MODEL_SOURCE=local && exec \"$@\"", "--"]
