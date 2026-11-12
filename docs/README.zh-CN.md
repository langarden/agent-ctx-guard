# agent-ctx-guard（中文）

> **压缩是过程，可验证才是结果。**  
> 面向 Agent 会话的可验证上下文压缩——折叠、可逆解压、防篡改账本。

`agent-ctx-guard` 把长会话转录压成小体积的元数据摘要，同时把**每条原始消息**保留在哈希校验的存档中。账本是防篡改的 JSONL 哈希链；存档可逐字节校验；摘要只含元数据——所以你可以发布"压掉了什么"的证明，**而不泄漏原文**。它是 **Verifiable-agent 家族**成员。

## 为什么需要它

上下文压缩是 Agent 圈当前最热的话题。但大多数压缩器是黑盒——你永远不知道**丢掉了什么**。这个库回答了这个问题：压缩是一个*过程*，`agent-ctx-guard` 让它变成*可验证的结果*。这是把 memory-ledger 的方法论用到会话压缩上：**折叠 → 可逆还原 → 证明什么都没丢**。

**你能得到：**

- **`fold()`** —— 归档原始消息，向防篡改账本追加一条仅含元数据的摘要
- **`unfold()`** —— 从存档还原精确的原始消息，sha256 校验（可检出存档篡改）
- **`verify()`** / **`verify_archive()`** —— 同时证明账本链与存档未被篡改
- **默认隐私** —— 摘要默认不含原文（可自定义）；原文只存在于哈希校验的存档中
- 零依赖，纯 Python 3.9+ 标准库

## 安装

```bash
pip install agent-ctx-guard
```

## 快速开始

```python
from agent_ctx_guard import CtxFolder

folder = CtxFolder(path_prefix="./my_session")   # 生成 .ctxg.ledger.jsonl + .ctxg.archive.jsonl

# 把每条即将滚出活动窗口的消息折叠
for msg in transcript:
    entry = folder.fold(msg)          # entry["summary"] 是元数据

# 之后还原一条精确原文
restored = folder.unfold(entry["message_id"])
print(restored["content"])

# 随时证明完整性
assert folder.verify() is True        # 账本链未被篡改
assert folder.verify_archive() is True
```

## 实测输出

```
$ python -m agent_ctx_guard
=== ledger entries (metadata-only summaries) ===
{'message_id': '8a845d8f', 'summary': {'role': 'user', 'content_length': 35, 'content_sha256': '482635470c5f087c', 'tokens': 0, 'type': ''}, 'payload_hash': 'f0b074c31dbf'}
ledger verify: True
archive verify: True
=== unfold restored message 2 ===
I see the token refresh cache is stale after expiry. I'll patch auth.py and add unit tests for the refresh path.
```

注意：账本里**完全不含原始正文**——只有角色 / 长度 / 摘要哈希。证明存在于哈希链，内容存留在已校验的存档，`unfold()` 逐字节还原精确原文。

## 设计不变量

| # | 不变量 | 由谁保证 |
|:--|:--|:--|
| 1 | 账本是 sha256 哈希链 | `fold()` + `verify()` |
| 2 | 解压时存档哈希必须匹配 | `unfold()` |
| 3 | 摘要默认不携带原始密钥 | `default_summary` |
| 4 | 从磁盘重载保持链与存档 | `CtxFolder.__init__` |
| 5 | 空账本 verify=True（创世） | `verify()` |

## Roadmap 想法

- CLI（`ctx-guard fold --file ... --ranges ...`）
- 通过自定义 `summary_fn` 接入 LLM 摘要
- 带前缀缓存感知的批量压缩区间选择

## 许可证

MIT。