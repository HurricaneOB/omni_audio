# 第一阶段环境配置手册：VSCode Remote SSH + uv + tmux

本手册严格按服务器《新用户入组指南》的存储和环境规范编写。第一阶段是 CPU 数据工程，不运行 Qwen3-Omni，也不需要 GPU。

## 1. 目录原则

服务器上遵守：

```text
/mdr5/home/$USER/                 代码、.venv、日志
/ky200t/datasets/$USER/           全量音频数据集、大型中间数据
/                                 禁止写用户数据
```

推荐最终布局：

```text
/mdr5/home/$USER/finance_audio_qwen3_omni_sujet_v1/           # 代码
/ky200t/datasets/$USER/finance_audio_qwen3_omni_sujet_v1/     # 全量数据
```

测试数据允许保存在代码目录：

```text
./data_test/offline_structure
./data_test/smoke_edge
./data_test/live
```

## 2. VSCode Remote SSH

1. 本地安装 VSCode 和 Remote - SSH。
2. 使用入组指南中的服务器地址/端口登录。
3. 打开 `/mdr5/home/你的用户名/`。
4. 把本项目 ZIP 上传后解压。

```bash
cd /mdr5/home/$USER
unzip finance_audio_qwen3_omni_sujet_v1.zip
cd finance_audio_qwen3_omni_sujet_v1
```

## 3. 用 uv 创建虚拟环境

服务器已全局安装 uv。不要在系统 Python 或 conda base 里直接 `pip install`。

```bash
cd /mdr5/home/$USER/finance_audio_qwen3_omni_sujet_v1
uv venv --python 3.10
source .venv/bin/activate
uv pip install pip
uv pip install -r requirements.txt
uv pip install -e .
```

验证：

```bash
which python
python --version
python -c "import fin_audio; print(fin_audio.__version__)"
python -c "import edge_tts, datasets, soundfile; print('imports ok')"
```

`which python` 应指向项目 `.venv/bin/python`。

## 4. FFmpeg 检查

```bash
which ffmpeg
ffmpeg -version | head
```

项目不会尝试 `sudo apt install`。如果服务器没有 ffmpeg，请联系管理员安装。

## 5. Hugging Face 缓存位置

全量任务不要把大型 cache 堆在家目录。建议：

```bash
mkdir -p /ky200t/datasets/$USER/.cache/huggingface
export HF_DATASETS_CACHE=/ky200t/datasets/$USER/.cache/huggingface
```

full 命令同时显式传：

```bash
--hf-cache-dir /ky200t/datasets/$USER/.cache/huggingface
```

## 6. 不需要 GPU

本阶段不启动 CUDA 训练、不占用 GPU，只执行 datasets + Edge-TTS + FFmpeg + Audio QC。

## 7. 长任务必须使用 tmux

```bash
tmux new -s sujet_audio_full
```

进入 tmux 后：

```bash
cd /mdr5/home/$USER/finance_audio_qwen3_omni_sujet_v1
source .venv/bin/activate
```

分离：`Ctrl+B`，然后按 `D`。

重新进入：

```bash
tmux attach -t sujet_audio_full
```

完成后：

```bash
tmux kill-session -t sujet_audio_full
```


## 8. v1.0.1 smoke 网络要求

- `offline-smoke`：不需要 Edge 网络，生成 `test-tone`，只测结构。
- `smoke`：需要访问 Edge-TTS，使用本地 fixture，输出可试听真实金融问题。
- `live-smoke`：需要 Hugging Face + Edge-TTS。
- `full`：需要 Hugging Face（首次/无 frozen parquet 时）+ Edge-TTS。

不要再把 `offline-smoke` 的测试音作为语义验收依据。
