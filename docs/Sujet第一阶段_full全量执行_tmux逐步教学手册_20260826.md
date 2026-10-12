# Sujet 第一阶段 full 全量执行：tmux 从测试到全量逐步教学手册
## 适用版本：原工程 + v1.0.1 smoke-fix replacement

> 目标：严格避免旧 mock/test-tone 结果混入正式 full，并指导你从 replacement 校验、真实 Edge 小样本测试、NAS 路径设置、tmux 长任务启动、监控、中断恢复到最终验收。
>
> **原则：先验证 replacement → pytest → smoke → live-smoke → 新建干净 FULL_ROOT → tmux full → 全量后抽检。**

---

# 0. 执行前约定

假设代码工程：

```text
~/omni_audio
```

正式数据计划放：

```text
/ky200t/datasets/$USER/
```

当前第一阶段：

```text
不需要 GPU
不需要 CUDA
不下载 Qwen3-Omni
不训练模型
```

因此：

```text
不用占 GPU
```

但长时间 Edge-TTS 网络任务必须使用：

```text
tmux
```

---

# 1. 第一步：进入代码工程

```bash
cd ~/omni_audio
```

确认：

```bash
pwd
```

应该类似：

```text
/mdr5/home/<username>/omni_audio
```

检查：

```bash
ls
```

至少应看到：

```text
configs
scripts
src
tests
docs
run_build.sh
requirements.txt
```

---

# 2. 激活 uv 虚拟环境

```bash
source .venv/bin/activate
```

确认：

```bash
echo "$VIRTUAL_ENV"
which python
python --version
```

Python 应来自：

```text
~/omni_audio/.venv/
```

---

# 3. 确认 FFmpeg

```bash
which ffmpeg
```

必须有路径。

然后：

```bash
ffmpeg -version | head -n 1
```

如果没有：

```text
ffmpeg
```

不要继续。

---

# 4. 确认 Edge-TTS

```bash
python - <<'PY'
import edge_tts
print("edge_tts import PASS")
PY
```

然后：

```bash
edge-tts --list-voices | head -n 20
```

如果能看到英语 voice，说明 Edge voice discovery 基本可用。

---

# 5. 非常重要：验证 replacement 确实覆盖成功

因为你使用的是：

```text
replacement 部分覆盖
```

所以 full 前先做合同检查。

---

## 5.1 检查 full 是否硬编码 Edge

```bash
grep -n -A12 -B3 'full)' run_build.sh
```

你必须看到：

```text
TTS_BACKEND="edge"
```

---

## 5.2 检查 smoke 也是 Edge

```bash
grep -n -A12 -B3 'smoke)' run_build.sh
```

`smoke)` 必须包含：

```text
TTS_BACKEND="edge"
```

而：

```text
offline-smoke)
```

才允许：

```text
TTS_BACKEND="test-tone"
```

---

## 5.3 检查 backend guard 文件存在

```bash
ls -l scripts/07_verify_tts_backend.py
```

必须存在。

---

## 5.4 检查 edge_client 不再有隐式 espeak fallback

```bash
grep -n 'test-tone\|backend == "edge"\|Communicate' \
  src/fin_audio/edge_client.py
```

应该看到：

```text
backend == "edge"
Communicate
backend == "test-tone"
```

不应该出现：

```text
找不到 espeak 就自动 sine
```

---

# 6. 可选：核对 replacement 关键文件 SHA256

如果你没有修改这些核心文件，可以执行：

```bash
sha256sum \
  run_build.sh \
  src/fin_audio/edge_client.py \
  src/fin_audio/voice_manager.py \
  src/fin_audio/env_check.py \
  scripts/07_verify_tts_backend.py \
  tests/test_smoke_mode_contract.py
```

当前 replacement 对应值：

```text
e5ca20b32e4d86d7a7d18c5819652c340fbe5adfcc20ac24201d16001f954a68  run_build.sh
01e3efd36ef0e3ac062e53918fa5b0f766e3519822dd7dd31cf9583b19d83d71  src/fin_audio/edge_client.py
f33226321d4dcaea9004a7aa5447a1308058800a69a98b15448d644700e3aa9c  src/fin_audio/voice_manager.py
9a82bdc1be059589e9b91de308697725611c1d4250812078beada5615815d376  src/fin_audio/env_check.py
dca23d9917ea7fa94f658af106bbaeb9194218de53cd6647dff8d6e47a936829  scripts/07_verify_tts_backend.py
e0374a5f43000a9e44ffe32ad3d3a032d7bca3abb0758dc1bdc2e9aeffe46164  tests/test_smoke_mode_contract.py
```

如果你自己后续编辑过中文注释，SHA 可能变化。

这种情况下不要只看 SHA，重点仍是：

```text
full → edge
smoke → edge
offline-smoke → test-tone
07 backend guard 存在
```

---

# 7. 运行全部单元测试

```bash
PYTHONPATH=src pytest -q
```

replacement 后当前工程应包含新增 smoke contract 测试。

目标：

```text
0 failed
```

我们修复版本的基线是：

```text
12 passed
```

如果不是全通过：

```text
不要进入 full
```

---

# 8. 删除旧版无语义 smoke 结果

只删除旧测试产物：

```bash
rm -rf ./data_test/mock
rm -rf ./examples/smoke_evidence
```

不要删除：

```text
src/
scripts/
configs/
tests/
```

---

# 9. 第一层真实语音 Gate：smoke

新版：

```text
smoke
= 本地 fixture
+ 真实 Edge-TTS
```

先清理旧 smoke_edge：

```bash
rm -rf ./data_test/smoke_edge
```

然后：

```bash
bash run_build.sh --mode smoke
```

---

# 10. smoke 成功时必须看到什么？

结尾必须出现类似：

```text
[BACKEND-GUARD][PASS] backend=edge
```

如果没有：

```text
不要 full
```

检查：

```bash
cat data_test/smoke_edge/manifests/edge_voice_snapshot.json
```

必须：

```json
"backend": "edge"
```

---

# 11. smoke 真实试听

查看 WAV：

```bash
find data_test/smoke_edge/audio_16k \
  -name '*.wav' \
  | head -n 10
```

至少人工试听：

```text
3～5 条
```

然后对某条 WAV 查对应的问题：

```bash
WAV="$(find data_test/smoke_edge/audio_16k -name '*.wav' | head -n 1)"
echo "$WAV"
```

查询：

```bash
python - "$WAV" <<'PY'
import json
import sys
from pathlib import Path

wav = Path(sys.argv[1]).resolve()
sid = wav.stem
p = Path("data_test/smoke_edge/manifests/provenance.jsonl")

for line in p.open(encoding="utf-8"):
    if not line.strip():
        continue
    row = json.loads(line)
    if row["id"] == sid:
        print("QUESTION:", row["source_user_text"])
        print("TTS TEXT:", row["tts_text"])
        print("ANSWER:", row["assistant_text"])
        print("WAV:", row["audio_wav"])
        break
PY
```

你试听内容应与：

```text
TTS TEXT
```

语义一致。

---

# 12. 第二层真实数据 Gate：live-smoke

不要只使用 fixture。

full 前还必须用真实 Sujet。

建议不再只测试 5 条，而测试：

```text
20 条
```

创建 HF cache：

```bash
mkdir -p /ky200t/datasets/$USER/.cache/huggingface

mkdir -p /ky200t/datasets/fengyumeng/.cache/huggingface
```

清理旧 live gate：

```bash
rm -rf ./data_test/live_full_gate
```

运行：

```bash
bash run_build.sh \
  --mode live-smoke \
  --output-root ./data_test/live_full_gate \
  --limit 20 \
  --hf-cache-dir /ky200t/datasets/$USER/.cache/huggingface
```

---

# 13. live-smoke 必须满足

结尾：

```text
[BACKEND-GUARD][PASS] backend=edge
```

检查：

```bash
cat data_test/live_full_gate/reports/FINAL_BUILD_REPORT.md
```

重点：

```text
TTS success > 0
Audio QC pass > 0
Final static validation errors = 0
```

---

# 14. 验证 live-smoke 的 20 条全部是 Edge plan

```bash
python - <<'PY'
import json
from pathlib import Path
from collections import Counter

p = Path("data_test/live_full_gate/prepared/tts_plan.jsonl")
rows = [json.loads(x) for x in p.open(encoding="utf-8") if x.strip()]

c = Counter(r.get("tts_backend") for r in rows)

print("rows =", len(rows))
print("backend =", c)

assert c == {"edge": len(rows)}
print("PASS")
PY
```

---

# 15. live-smoke 至少试听 5 条

列出：

```bash
find data_test/live_full_gate/audio_16k \
  -name '*.wav' \
  | head -n 20
```

至少随机或人工选择：

```text
5 条
```

确认：

```text
问题可理解
没有正弦测试音
与 provenance 的 tts_text 一致
```

只有通过后才进入 full。

---

# 16. 第一次 full：选择一个干净的正式目录

推荐：

```bash
export FULL_ROOT=/ky200t/datasets/$USER/finance_audio_qwen3_omni_sujet_v1
export HF_CACHE=/ky200t/datasets/$USER/.cache/huggingface

export FULL_ROOT=/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1
export HF_CACHE=/ky200t/datasets/fengyumeng/.cache/huggingface
```

显示：

```bash
echo "$FULL_ROOT"
echo "$HF_CACHE"
```

---

# 17. 检查 FULL_ROOT 是否干净

```bash
if [ -d "$FULL_ROOT" ]; then
  echo "目录已存在，下面显示前 30 个文件："
  find "$FULL_ROOT" -mindepth 1 -type f | head -n 30
else
  echo "FULL_ROOT 尚不存在：这是第一次 full 的理想状态"
fi
```

如果出现：

```text
旧 mock
test-tone
不清楚来源的 audio_16k
旧 tts_status
```

不要复用。

选择一个新目录：

```bash
export FULL_ROOT=/ky200t/datasets/$USER/finance_audio_qwen3_omni_sujet_v1_full_20260826
```

---

# 18. 创建并检查 NAS 写权限

```bash
mkdir -p "$FULL_ROOT"
mkdir -p "$HF_CACHE"
```

写权限：

```bash
touch "$FULL_ROOT/.write_test"
rm "$FULL_ROOT/.write_test"
```

容量：

```bash
df -h "$FULL_ROOT"
```

---

# 19. 为什么 full 一定要 tmux？

全量约数万条 Edge-TTS。

如果普通 SSH：

```text
网络断开
VSCode Remote 断线
本地电脑休眠
```

任务可能受到影响。

所以使用：

```text
tmux
```

---

# 20. 创建 full tmux 会话

```bash
tmux new -s sujet_audio_full
```

进入后，你会处于 tmux shell。

---

# 21. tmux 内重新进入项目

```bash
cd ~/omni_audio
```

激活：

```bash
source .venv/bin/activate
```

确认：

```bash
which python
which ffmpeg
```

---

# 22. tmux 内重新设置路径变量

不要假定外部 shell 的 export 一定被保留。

在 tmux 内重新执行：

```bash
export FULL_ROOT=/ky200t/datasets/$USER/finance_audio_qwen3_omni_sujet_v1
export HF_CACHE=/ky200t/datasets/$USER/.cache/huggingface
```

如果你在第 17 步选择了带日期的新目录，就使用那个实际路径。

确认：

```bash
echo "$FULL_ROOT"
echo "$HF_CACHE"
```

---

# 23. 正式 full 命令

运行：

```bash
bash run_build.sh \
  --mode full \
  --output-root "$FULL_ROOT" \
  --hf-cache-dir "$HF_CACHE"
```

---

# 24. full 内部会自动做什么？

你只执行一次命令。

程序自动：

```text
Environment check
↓
自动下载/加载 Sujet
↓
冻结 raw/sujet_train.parquet
↓
筛 task_type == qa
↓
qa_source.jsonl
↓
finance TTS normalization
↓
动态发现真实 Edge English voices
↓
tts_plan.jsonl
↓
真实 Edge-TTS
↓
FFmpeg
↓
16 kHz mono PCM16 WAV
↓
Audio QC
↓
Qwen3-Omni JSONL
↓
Final static validation
↓
Backend guard
↓
FINAL_BUILD_REPORT
```

---

# 25. tmux 如何安全离开？

任务运行时：

```text
Ctrl+B
```

松开，再按：

```text
D
```

这是 detach。

不要使用：

```text
Ctrl+C
```

---

# 26. 如何查看 tmux 是否还在？

重新 SSH 后：

```bash
tmux ls
```

应该看到：

```text
sujet_audio_full
```

---

# 27. 如何重新进入？

```bash
tmux attach -t sujet_audio_full
```

---

# 28. 在第二个终端查看 full 日志

进入代码工程：

```bash
cd ~/omni_audio
```

查看最新日志：

```bash
LATEST_LOG="$(ls -1t logs/full_*.log | head -n 1)"
echo "$LATEST_LOG"
```

实时：

```bash
tail -f "$LATEST_LOG"
```

---

# 29. 查看已经生成多少 WAV


```bash
find "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1/audio_16k" \
  -type f \
  -name '*.wav' \
  | wc -l
```

---

# 30. 查看已经准备多少 QA

```bash
wc -l "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1/prepared/qa_source.jsonl"
```

---

# 31. 查看 TTS status 数量

```bash
wc -l "$FULL_ROOT/manifests/tts_status.jsonl"
```

状态分布：

```bash
python - "$FULL_ROOT" <<'PY'
import json
import sys
from collections import Counter
from pathlib import Path

p = Path(sys.argv[1]) / "manifests" / "tts_status.jsonl"
c = Counter()

if p.exists():
    for line in p.open(encoding="utf-8"):
        if line.strip():
            c[json.loads(line).get("tts_status")] += 1

print(c)
PY
```

---

# 32. 查看 Audio QC 状态

```bash
python - "$FULL_ROOT" <<'PY'
import json
import sys
from collections import Counter
from pathlib import Path

p = Path(sys.argv[1]) / "manifests" / "audio_qc.jsonl"
c = Counter()

if p.exists():
    for line in p.open(encoding="utf-8"):
        if line.strip():
            c[json.loads(line).get("audio_qc")] += 1

print(c)
PY
```

---

# 33. 长任务中断怎么办？

如果：

```text
SSH 断开
Edge 短时失败
进程被人为终止
```

当前工程支持 resume。

只要这确实是：

```text
同一次 full 的 output root
```

重新：

```bash
tmux attach -t sujet_audio_full
```

如果原进程已经不存在，则：

```bash
cd ~/omni_audio
source .venv/bin/activate

export FULL_ROOT=/之前完全相同的full目录
export HF_CACHE=/之前完全相同的cache目录
```

重新：

```bash
bash run_build.sh \
  --mode full \
  --output-root "$FULL_ROOT" \
  --hf-cache-dir "$HF_CACHE"
```

已存在的成功 WAV 会被复用。

---

# 34. 哪些情况下不能直接 resume？

不要对以下目录执行 full resume：

```text
旧 mock 输出
offline-smoke
smoke_edge
live-smoke
来源不明的旧 full
```

resume 只应该用于：

```text
明确由当前 replacement 版本 full=edge 创建的同一个 FULL_ROOT
```

---

# 35. full 结束时必须看到 Backend Guard

最终终端必须出现：

```text
[BACKEND-GUARD][PASS] backend=edge
```

如果出现：

```text
[BACKEND-GUARD][FAIL]
```

则：

```text
不能交付训练
```

---

# 36. full 结束后第一件事：看报告

```bash
cat "$FULL_ROOT/reports/FINAL_BUILD_REPORT.md"

cat "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1/reports/FINAL_BUILD_REPORT.md"
```

重点：

```text
QA rows
TTS success / failed
Audio QC pass / fail / long
Final rows
Train / Valid
Total audio hours
Final static validation errors
```

必须：

```text
Final static validation errors = 0
```

---

# 37. 查看机器可读 summary

```bash
python -m json.tool \
  "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1/manifests/build_summary.json"
```

---

# 38. 确认所有 TTS plan 都是 Edge

```bash
python - "python -m json.tool \
  "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1/manifests/build_summary.json" <<'PY'
import json
import sys
from collections import Counter
from pathlib import Path

p = Path(sys.argv[1]) / "prepared" / "tts_plan.jsonl"
rows = [json.loads(x) for x in p.open(encoding="utf-8") if x.strip()]
c = Counter(r.get("tts_backend") for r in rows)

print(c)
assert c == {"edge": len(rows)}
print("PASS")
PY
```

---

# 39. 确认 voice snapshot 是 Edge

```bash
python -m json.tool \
  "python -m json.tool \
  "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1/manifests/edge_voice_snapshot.json"
```

必须：

```json
"backend": "edge"
```

---

# 40. 确认 train + valid = all

```bash
python - "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])

def n(p):
    return sum(1 for x in p.open(encoding="utf-8") if x.strip())

all_n = n(root / "final/all.jsonl")
train_n = n(root / "final/train.jsonl")
valid_n = n(root / "final/valid.jsonl")

print(all_n, train_n, valid_n)
assert all_n == train_n + valid_n
print("PASS")
PY
```

---

# 41. 确认所有训练音频存在

```bash
python - "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
missing = []
total = 0

for line in (root / "final/all.jsonl").open(encoding="utf-8"):
    if not line.strip():
        continue
    row = json.loads(line)
    total += 1
    for x in row["audios"]:
        if not Path(x).exists():
            missing.append(x)

print("total =", total)
print("missing =", len(missing))
assert not missing
print("PASS")
PY
```

---

# 42. 最重要：全量后随机语义抽检

技术 QC 通过以后，还必须抽查真实 Edge 语音。

生成 30 条 audit：

```bash
python - "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1" <<'PY'
import csv
import json
import random
import sys
from pathlib import Path

root = Path(sys.argv[1])
src = root / "manifests/provenance.jsonl"
dst = root / "reports/random_audio_audit_30.tsv"

rows = [
    json.loads(x)
    for x in src.open(encoding="utf-8")
    if x.strip()
]

sample = random.Random(20260826).sample(rows, min(30, len(rows)))

with dst.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow([
        "id",
        "source_user_text",
        "tts_text",
        "assistant_text",
        "audio_wav",
        "voice",
        "locale",
        "rate",
        "duration_sec"
    ])

    for r in sample:
        w.writerow([
            r["id"],
            r["source_user_text"],
            r["tts_text"],
            r["assistant_text"],
            r["audio_wav"],
            r["voice"],
            r.get("voice_locale"),
            r["rate"],
            r.get("duration_sec"),
        ])

print(dst)
PY
```

查看：

```bash
less -S "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1/reports/random_audio_audit_30.tsv"
```

从中人工试听至少：

```text
10 条
```

最好：

```text
30 条
```

---

# 43. 语义抽检看什么？

逐条确认：

```text
[ ] 不是 test tone
[ ] 能听到英语问题
[ ] 问题与 tts_text 一致
[ ] 语速可理解
[ ] 金融数字/缩写没有明显灾难性读错
[ ] WAV 没有异常截断
```

这一步补足：

```text
技术 Audio QC
```

不能覆盖的语义可听性风险。

---

# 44. 怎么展示某一条真实样本？

从 provenance 中随机找一条：

```bash
python - "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1" <<'PY'
import json
import random
import sys
from pathlib import Path

p = Path(sys.argv[1]) / "manifests/provenance.jsonl"
rows = [json.loads(x) for x in p.open(encoding="utf-8") if x.strip()]
r = random.Random(1).choice(rows)

print("QUESTION:")
print(r["source_user_text"])

print("\nTTS TEXT:")
print(r["tts_text"])

print("\nANSWER:")
print(r["assistant_text"])

print("\nWAV:")
print(r["audio_wav"])

print("\nVOICE:")
print(r["voice"], r.get("voice_locale"), r["rate"])
PY
```

---

# 45. 查看最终训练格式

```bash
head -n 1 "/ky200t/datasets/fengyumeng/finance_audio_qwen3_omni_sujet_v1/final/train.jsonl" \
  | python -m json.tool
```

你应该看到：

```text
messages
audios
```

其中：

```text
user:
<audio>Please answer the financial question in the audio.

assistant:
原始 Sujet answer

audios:
绝对 WAV 路径
```

---

# 46. 最终训练工程师交接路径

```bash
echo "$FULL_ROOT/final/train.jsonl"
echo "$FULL_ROOT/final/valid.jsonl"
echo "$FULL_ROOT/audio_16k"
echo "$FULL_ROOT/manifests/provenance.jsonl"
echo "$FULL_ROOT/reports/FINAL_BUILD_REPORT.md"
```

---

# 47. 训练工程师如何接入 ms-swift？

第一阶段只负责数据。

当前 ms-swift 自定义数据集支持：

```text
--dataset
--val_dataset
```

因此交接给训练工程师：

```bash
DATA_ROOT=/ky200t/datasets/<USER>/finance_audio_qwen3_omni_sujet_v1

--dataset "$DATA_ROOT/final/train.jsonl" \
--val_dataset "$DATA_ROOT/final/valid.jsonl"
```

其他模型、LoRA、GPU 和训练超参由后续训练工程决定。

---

# 48. 一次性 full 最终 Gate

在正式开始 full 前：

```text
Gate A
[ ] FFmpeg OK
[ ] Edge-TTS OK
[ ] pytest 0 failed
[ ] replacement 合同检查通过

Gate B
[ ] smoke backend=edge
[ ] smoke BACKEND-GUARD PASS
[ ] smoke 试听 3～5 条

Gate C
[ ] live-smoke 20 条真实 Sujet
[ ] live-smoke BACKEND-GUARD PASS
[ ] live-smoke Final validation = 0
[ ] 试听至少 5 条

Gate D
[ ] FULL_ROOT 是干净独立目录
[ ] HF_CACHE 在 /ky200t
[ ] FULL_ROOT 可写
[ ] NAS 空间足够
```

只有全部通过：

```text
tmux → full
```

---

# 49. full 结束后的最终 Gate

```text
[ ] BACKEND-GUARD PASS
[ ] edge_voice_snapshot backend=edge
[ ] tts_plan 全部 backend=edge
[ ] final_validation_error_count == 0
[ ] all == train + valid
[ ] final 所有 audio path 存在
[ ] provenance 映射完整
[ ] 随机语义抽检通过
```

完成后，这批数据才建议正式交给模型训练工程师。

---

# 50. 最简正式执行命令

通过全部前置 Gate 后：

```bash
tmux new -s sujet_audio_full
```

tmux 内：

```bash
cd ~/omni_audio
source .venv/bin/activate

export FULL_ROOT=/ky200t/datasets/$USER/finance_audio_qwen3_omni_sujet_v1
export HF_CACHE=/ky200t/datasets/$USER/.cache/huggingface

mkdir -p "$FULL_ROOT" "$HF_CACHE"

bash run_build.sh \
  --mode full \
  --output-root "$FULL_ROOT" \
  --hf-cache-dir "$HF_CACHE"
```

detach：

```text
Ctrl+B
D
```

重新进入：

```bash
tmux attach -t sujet_audio_full
```

---

# 51. 最终结论

当前 replacement 后：

```text
full
```

已经固定走：

```text
真实 Edge-TTS
```

不会主动进入：

```text
test-tone
```

旧版无语义正弦波问题的具体代码路径已经被切断。

但工程上仍应坚持：

```text
真实小样本 Gate
+
干净 FULL_ROOT
+
backend provenance guard
+
技术 QC
+
full 后随机语义抽检
```

这样才是把“代码路径正确”进一步提升为“正式数据资产可信”的完整验收流程。
