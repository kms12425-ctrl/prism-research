可以做，但只能做“单卡缩规模的相对对比”，不能复现论文第 7 节那种结论级 benchmark。对你这张共享的 A6000，合理目标是比较 Static colocate、Elastic colocate、Prism-style scheduling 在同一块 GPU、同一组小模型、同一负载下的 TTFT、TPOT、SLO attainment 和吞吐，而不是去追论文里的 58 模型、8 到 32 GPU、TP=4/8、大规模真实 trace 数字。

我已经把计划保存到会话计划里。基于仓库现状，当前可依赖的入口是 [benchmark/multi-model/benchmark.py](benchmark/multi-model/benchmark.py#L1740)、[benchmark/multi-model/trace.py](benchmark/multi-model/trace.py#L243) 和 README 里更新过的 1-GPU 示例 [README.md](README.md#L117)。需要注意，辅助脚本 [scripts/run_collocate_static.sh](scripts/run_collocate_static.sh#L6)、[scripts/run_collocate.sh](scripts/run_collocate.sh#L6)、[scripts/run_ours.sh](scripts/run_ours.sh#L6) 还在引用当前工作区里不存在的旧配置名，所以不适合直接照跑。

## Plan: 单卡 A6000 Benchmark 可行性

建议路线是先验证环境和最小可运行配置，再逐步放大到“可解释的单卡对比”。

**Steps**
1. 先做环境确认，只用最小配置验证 Redis、模型下载、服务启动和 benchmark 输出路径是否正常。
2. 以当前真实存在的 1-GPU 配置为准，不使用旧脚本引用的失效配置。
3. 第一阶段跑单模型 smoke，使用 [benchmark/multi-model/model_configs/1_gpu_1_model_smoke.json](benchmark/multi-model/model_configs/1_gpu_1_model_smoke.json) 建立你这张 A6000 上的独占基线。
4. 第二阶段跑双模型 smoke，使用 [benchmark/multi-model/model_configs/1_gpu_2_model_smoke.json](benchmark/multi-model/model_configs/1_gpu_2_model_smoke.json)，在低 req-rate 下确认共享 GPU 上能稳定出 TTFT 和 TPOT。
5. 第三阶段做真正的相对比较，优先尝试 2 个 3B 模型的 Prism-style 配置 [benchmark/multi-model/model_configs/1_gpu_2_model_our.json](benchmark/multi-model/model_configs/1_gpu_2_model_our.json)，然后再视显存余量尝试 2 个 8B 的 static 和 elastic 配置 [benchmark/multi-model/model_configs/1_gpu_2_model_colocate_static.json](benchmark/multi-model/model_configs/1_gpu_2_model_colocate_static.json) 与 [benchmark/multi-model/model_configs/1_gpu_2_model_colocate_elastic.json](benchmark/multi-model/model_configs/1_gpu_2_model_colocate_elastic.json)。
6. SLO 不要直接套论文阈值，而是在你自己的 A6000 上先测每个模型独占运行时的 P95 TTFT 和 P95 TPOT，再按论文同样的方法乘 scale 因子。
7. 对比时固定模型对、seed、输入输出长度范围、req-rate、time-scale，只比较模式差异。
8. 如果共享显卡导致显存碎片或被他人占用，优先降模型规模和负载，不要强行跑 8B 双模型。

**Relevant files**
- [benchmark/multi-model/benchmark.py](benchmark/multi-model/benchmark.py#L1755)  
  主要 benchmark 入口，支持 req-rate、real-trace、time-scale、replication、policy 和结果落盘。
- [benchmark/multi-model/trace.py](benchmark/multi-model/trace.py#L417)  
  真实 trace 和 SLO scale 逻辑都在这里。
- [benchmark/multi-model/model_configs/1_gpu_1_model_smoke.json](benchmark/multi-model/model_configs/1_gpu_1_model_smoke.json)  
  最低风险启动配置。
- [benchmark/multi-model/model_configs/1_gpu_2_model_smoke.json](benchmark/multi-model/model_configs/1_gpu_2_model_smoke.json)  
  最安全的双模型共享测试。
- [benchmark/multi-model/model_configs/1_gpu_2_model_our.json](benchmark/multi-model/model_configs/1_gpu_2_model_our.json)  
  单卡 Prism-style 候选配置。
- [benchmark/multi-model/model_configs/1_gpu_2_model_colocate_static.json](benchmark/multi-model/model_configs/1_gpu_2_model_colocate_static.json)  
  Static baseline 候选。
- [benchmark/multi-model/model_configs/1_gpu_2_model_colocate_elastic.json](benchmark/multi-model/model_configs/1_gpu_2_model_colocate_elastic.json)  
  Elastic baseline 候选。
- [README.md](README.md#L117)  
  当前与现有 1-GPU 配置名对齐的示例命令。
- [install.md](install.md#L1)  
  Redis 和依赖前提。

**Verification**
1. 跑单模型 smoke，确认服务稳定、benchmark-results 和 output-requests 里有结果文件。
2. 跑双模型 smoke，确认不会立刻 OOM，且 TTFT、TPOT 能正常输出。
3. 对每个候选模型先做独占跑分，拿到本地 P95 TTFT 和 TPOT。
4. 用同一组参数分别跑 static、elastic、Prism-style，对比 attainment 和 throughput。
5. 如果某一组模式因为共享 GPU 干扰失败，只降低负载或模型，不改变比较方法。

**Decisions**
- 可以做：单卡 A6000 上的相对 benchmark 对比。
- 不建议做：论文规模的 58 模型、32 GPU、70B TP 实验。
- 当前仓库里能直接支撑的 baseline 主要是 static、elastic 和 Prism-style。
- 论文里写的 MuxServe++ 和 QLM，我在当前仓库没有找到对应实现入口，所以不能把“和所有论文 baseline 完整复现”作为计划的一部分。

结论很直接：你可以做 benchmark，而且能做出有意义的 baseline 对比，但前提是接受缩规模。最稳妥的目标是先在单卡上证明“Prism-style 策略相对 static 或 elastic，在你的受限环境里是更好还是更差”，而不是去验证论文里的绝对收益。

如果这个范围可以，我下一步可以继续把这个计划细化成一份具体执行清单，直接列出你该按什么顺序跑、先试哪组模型、每一步预期看什么结果。