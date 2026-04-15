# Introducing TWIST: Bringing Double-Helix Training to Hopper

**By:** The TWIST Team (USTC, PolyU(H.K.), NUS, IAI Hefei, MBZUAI)
**Date:** March 2026

---

## Key Highlights

- **3–6% absolute MFU gain** on a single H200 node and **up to 11% absolute MFU gain** on multi-node H800 clusters over Megatron-LM, near the ideal overlap ceiling
- **Upgraded Megatron-LM from v0.7.0 to v0.14.0**, adapting the system to the latest APIs
- **Matched production Megatron kernels** by integrating Flash Attention 3 and Transformer Engine GEMM
- **Removed redundant CUDA synchronizations**, reducing launch bubbles on high-end GPUs
- **Layer analysis** shows TWIST hides **83%** of exposed communication, leaving only **4.7%** visible

---

## What is TWIST?

**TWIST** (**TW**o-strand **I**nterleaved **S**cheduling for **T**raining) is an upgraded and rebranded version of **DHeLlam** (“Double-Helix LLM”), our micro-batch co-execution system for distributed LLM training published at **ICCD 2025** and awarded **Best Paper**. Its key idea is to **overlap one micro-batch’s forward pass with another’s backward pass** on the same GPU, hiding communication behind computation.

In distributed training with TP, SP, CP, and EP, each transformer layer involves collective communication such as AllGather, ReduceScatter, All-to-All, and Send/Recv, which can consume **20–55%** of training time.

DHeLlam addresses this with two mechanisms:

1. **Model Folding** — reshapes the pipeline into a W-pattern so forward and backward passes from two micro-batches coexist on each GPU, with **under 3%** extra memory overhead.
2. **Operator Pairing** — uses profiling and dynamic programming to pair forward and backward operators for maximum overlap under hardware constraints.

On Ampere GPUs (A40/A800), DHeLlam achieved **12–40%** higher throughput than Megatron-LM, reached **up to 64% MFU**, and hid **up to 83%** of communication overhead. For more information, please refer to our [paper](https://ieeexplore.ieee.org/document/11310905).

![Dhellam Overview.svg](Introducing%20TWIST%20Bringing%20Double-Helix%20Training%20t/Dhellam_Overview.svg)

*Figure 1: Double-strand execution in TWIST (DHeLlam) on 4 GPUs*

**The question is whether these gains carry over to Hopper.**

---

## The Challenge: Bringing TWIST to Hopper

Porting the original DHeLlam codebase from Ampere to Hopper was more than a rebuild. Three issues stood out:

1. **Framework mismatch** — DHeLlam was built on Megatron-LM v0.7.0, while Hopper requires newer support in Megatron v0.14.0+ for Flash Attention 3, Transformer Engine FP8, updated NCCL, and changed APIs.
2. **Kernel gap** — DHeLlam’s original custom GEMM and attention kernels were designed for Ampere. On Hopper, they cannot fully use newer hardware features (e.g., FP8 Tensor Cores, TMA (Tensor Memory Accelerator), and warp specialization), so matching Megatron’s FA3 and TE GEMM kernels was necessary for both performance and fair comparison.
3. **Synchronization overhead** — frequent `torch.cuda.synchronize()` calls introduced launch bubbles. This mattered little on Ampere, but on faster Hopper GPUs it caused visible idle time and reduced efficiency.

So while the core overlap idea remains the same, making it work well on Hopper required major updates to the framework, kernels, and execution flow — resulting in what we now call **TWIST**.

---

## What We Achieved

### Upgrade 1: Megatron-LM v0.7.0 → v0.14.0

We migrated TWIST's integration layer to work with Megatron-LM Core v0.14.0 (commit id: `23e00ed`). Key changes include:

- **MoE API migration**: Updated `GroupedMLP` and `TopKRouter` instantiation to pass the new `model_comm_pgs` parameter, and adapted to the new routing return format (`routing_probs, routing_map` instead of `probs, indices`)
- **Attention backend**: Replaced the original custom `pymha_varlen_fwd/bwd` with Megatron's `TEDotProductAttention`, which properly leverages Transformer Engine's Hopper-optimized attention paths
- **Transformer Engine API**: Updated LayerNorm calls from the deprecated `transformer_engine_extensions` to the new `transformer_engine_torch` interface with explicit dtype parameters
- **Dynamic GPU architecture detection**: `setup.py` now auto-detects all available CUDA devices and generates appropriate `gencode` flags, natively supporting sm_90 (Hopper)

### Upgrade 2: Flash Attention 3 + TE GEMM

To ensure a fair apples-to-apples comparison with Megatron-LM, we aligned TWIST's compute operators with Megatron's production kernels:

**Flash Attention 3**: Upgraded from FA2 to FA3, which exploits Hopper's asynchronous warp specialization for higher throughput. The training script now uses `--attention-backend flash` with FA3's Hopper-optimized paths.

**Transformer Engine GEMM**: Replaced the original custom GEMM kernels with TE's `general_gemm`:

```python
from transformer_engine.pytorch.cpp_extensions import general_gemm
```

This brings two benefits:

1. The GEMM kernels are identical to what Megatron uses — any throughput difference is purely from TWIST's scheduling, not from faster/slower kernels
2. FP8 quantization support (E4M3 for forward, E5M2 for backward) is available via `FP8QuantizerManager` for future exploration

We validated operator alignment with comprehensive test suites (`test/dense_operators/test_gemm_fp16.py`, `test_gemm_fp8.py`) confirming accuracy parity.

### Upgrade 3: Removing CUDA Synchronization Barriers

The original code contained `torch.cuda.synchronize()` calls after each operator pair's execution to ensure completion before proceeding. We identified this as unnecessary — PyTorch's CUDA stream semantics and event-based synchronization already guarantee correct ordering. The explicit host-device synchronization was a conservative safety measure that had become a performance bottleneck:

```python
# Before (removed):
if handle_status:
    torch.cuda.synchronize()  # Blocks CPU until ALL GPU work finishes

# After: rely on stream-level event synchronization
```

On Hopper, where individual kernels execute faster, the relative cost of a full device synchronization is amplified. Removing these barriers allows the CPU to stay ahead of the GPU, maintaining a healthy launch queue and eliminating idle gaps between kernels.

---

## Results

We evaluate TWIST’s dense model training optimization on both single-node and multi-node setups, both in Hopper platform.

### Single-Node Performance (Qwen3-14B-like, 8× H200)

#### Experimental Setup

| Parameter | Value |
| --- | --- |
| GPU | NVIDIA H200 × 8 |
| Model | Qwen3-14B-like config (40 layers, hidden=5120, FFN=17408, 40 Attn heads, 8 KV heads) |
| Global Batch Size | 100 |
| Micro Batch Size | 4 |
| Sequence Length | 8192 |

**Note:** The Qwen3-14B-like model excludes the computation of RoPE and QK Normalization. Support for RoPE and QK Normalization within the model’s computation graph in TWIST is currently under development.

#### End-to-End MFU

| Configuration | GPU Count | TP | PP |
| --- | --- | --- | --- |
| Config 1 | 8 | 4 | 2 |
| Config 2 | 8 | 8 | 1 |

![End-to-End MFU Comparison on H200](Introducing%20TWIST%20Bringing%20Double-Helix%20Training%20t/mfu_comparison.svg)

*Figure 2: MFU comparison between Megatron-LM and TWIST across TP/PP configurations on 8× H200 GPUs. TWIST achieves **+3% absolute MFU gain** on Config 1 (46% → 49%) and **+6% absolute MFU gain** on Config 2 (41% → 47%).*

Across both TP/PP configurations, TWIST delivers a consistent **3–6% absolute MFU improvement** over vanilla Megatron-LM on a single H200 node.

> **A note on fair comparison**: During development, we discovered that the original DHeLlam code had a bug causing backward gradients to be zero. This led to lower GPU power draw, higher boost clocks, and artificially faster kernel execution — inflating the apparent advantage. After fixing this bug and aligning all operators with Megatron’s implementations, the numbers above represent a genuine, reproducible improvement purely from TWIST’s communication-hiding scheduling.
> 

### Multi-Node Performance (Qwen3-32B-like, 32× H800)

We further validate TWIST at scale on a 4-node H800 cluster (32 GPUs total) using a Qwen3-32B-like model configuration across a range of parallelism strategies and sequence lengths.

#### Experimental Setup

| Parameter | Value |
| --- | --- |
| GPU | NVIDIA H800 × 32 (4 nodes × 8 GPUs) |
| Model | Qwen3-32B-like config (hidden=5120, FFN=25600, 64 Attn heads, 8 KV heads) |
| Global Batch Size | 400 |

#### End-to-End MFU

| TP | PP | DP | MBS | SEQ_LEN | Megatron MFU | TWIST MFU | Absolute MFU Gain |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 4 | 4 | 1 | 4K | 47.27% | 55.49% | +8.22% |
| 4 | 2 | 4 | 2 | 4K | 44.73% | 55.81% | +11.08% |
| 8 | 1 | 4 | 2 | 4K | 36.11% | 46.13% | +10.02% |
| 4 | 2 | 4 | 1 | 8K | 46.08% | 52.00% | +5.92% |
| 8 | 1 | 4 | 1 | 8K | 37.40% | 48.09% | +10.69% |

TWIST achieves impressively **6–11% absolute MFU gain** over Megatron-LM across all parallelism configurations on H800 clusters.

### Layer-Level Breakdown (Qwen3-14B-like, TP=8, PP=1)

To understand where the single-node gains come from, we profiled the execution time of a single transformer layer in Megatron-LM and TWIST under the Qwen3-14B-like model:

![Single Transformer Layer Breakdown](Introducing%20TWIST%20Bringing%20Double-Helix%20Training%20t/layer_breakdown.svg)

*Figure 3: Execution time breakdown of a single transformer layer under TP=8, PP=1. Megatron-LM exposes 5.4 ms of communication (25% of layer time), while TWIST hides 83% of it through double-strand co-execution, leaving only 0.9 ms exposed. The green dashed line marks the theoretical perfect-overlap limit where all communication is perfectly overlapped (16.5 ms).*

Key observations:

1. **83% of communication hidden**: Exposed communication dropped from 5.5 ms to 0.9 ms — TWIST successfully hides the vast majority of TP/SP collective overhead.
2. **Compute slowdown from co-execution is modest**: When forward compute and backward compute run concurrently, they interfere slightly (sharing SMs, memory bandwidth, L2 cache). The total compute time increased from 16.5 ms to 18.3 ms — a **10.9% slowdown** overall, with per-operator-pair slowdown under 13%.
3. **Residual exposed communication**: The remaining 0.9 ms comes from one AllGather at the beginning of each layer that cannot be overlapped (no backward operator is available to pair with), this is mainly because TWIST overlaps at layer level.
4. **Current vs. theoretical ceiling**: TWIST achieves **462 TFLOPS (47% MFU)**, while the theoretical perfect-overlap limit is **536 TFLOPS (54% MFU**, shown as the **green dashed line** in Figure 3) — a **7% absolute gap** that represents the cost of compute slowdown and the one unhidden AllGather.

---

## Insight: Why MFU is Still Below 60%

Even with perfect communication hiding, the theoretical MFU ceiling for Qwen3-like configurations on H200 is only ~54% — well below the 60%+. The root cause is **the model's narrow hidden dimension**.

Qwen3-14B and Qwen3-32B both use `hidden_size=5120`, which is relatively small for their parameter counts (achieved through more layers and a large FFN ratio rather than a wide hidden dimension). Under high tensor parallelism (TP=8), each GPU's GEMM dimensions become:

- QKV projection: `(5120/8) × 5120` = `640 × 5120`
- Output projection: `5120 × (5120/8)` = `5120 × 640`

These narrow matrix shapes cannot fully saturate H200's massive Tensor Core throughput. The GPU spends proportionally more time on memory access and kernel launch overhead relative to useful FLOPs. This is a fundamental model-architecture limitation, not a scheduling issue — no overlap strategy can push MFU beyond what the compute kernels themselves can achieve.

For models with wider hidden dimensions (e.g., LLaMA-3-70B with `hidden_size=8192`), we expect higher absolute MFU numbers since the per-GPU GEMM dimensions remain large enough to keep Tensor Cores busy even at high TP degrees.

---

## Summary and Future Work

By upgrading the original DHeLlam codebase to Megatron v0.14.0, aligning operators with FA3 and TE GEMM, and removing unnecessary CUDA synchronizations, we created **TWIST** — bringing double-helix co-execution to Hopper GPUs. TWIST achieves a clean **3–6% absolute MFU gain** on a single H200 node and **up to 12% absolute MFU gain** on multi-node H800 clusters over Megatron-LM.

Layer-level analysis shows TWIST’s key advantage still holds on Hopper: overlapping forward communication with backward computation hides **83%** of exposed communication, with only a **10.9%** compute slowdown.

Future work includes:

1. **Closing the remaining 7% gap** through finer-grained operator splitting and cross-layer pairing to reduce exposed AllGather and co-execution overhead.
2. **Exploring FP8 training** with TE GEMM, which may further reduce compute time but will require re-profiling overlap opportunities.
3. **Testing wider models** such as LLaMA3-70B and K2-V2, where higher per-GPU compute could increase MFU headroom.
4. **Extending to MoE + EP on Hopper**, where NCCL EP communication may create additional overlap opportunities.

The complete codebase is open-source at [github.com/DHelix-AI/dhelix](https://github.com/DHelix-AI/dhelix).

---

*TWIST (formerly DHeLlam) is jointly developed and maintained by University of Science and Technology of China, Hong Kong Polytechnic University, National University of Singapore, Institute of Artificial Intelligence, Hefei Comprehensive National Science Center and Mohamed bin Zayed University of Artificial Intelligence. The original paper "DHeLlam: Hiding Communication Cost in LLM Training via Micro-batch Co-execution" received the Best Paper Award at ICCD 2025.*