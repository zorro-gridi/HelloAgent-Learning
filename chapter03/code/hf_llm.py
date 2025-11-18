import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from huggingface_hub import snapshot_download

import socket
import socks
import os
from pathlib import Path
home_dir = Path(os.path.expanduser('~'))

import yaml

from pathlib import Path
current_dir = Path(__file__).parent

# 读取配置文件
with open(current_dir.parent.parent.parent / 'config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# # 端口应该使用【出站端口】
# socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 7897)
# socket.socket = socks.socksocket

# os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7897'
# os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7897'

# 指定模型ID
model_id = "Qwen/Qwen1.5-0.5B-Chat"
# 该模型需要申请访问
model_id = "meta-llama/Llama-3.2-3B"
model_id = "jinaai/jina-embeddings-v3"

model_dir = Path('/Volumes/pssd/llm/') / model_id

# NOTE: 下载模型到本地缓存 (如果容易断连，手动从网站下载)
# snapshot_download(
#     repo_id=model_id,
#     local_dir=model_dir,
#     token=config['hf_token-read'],
#     resume_download=True,
# )
# print("模型下载完成！")


# 设置设备，优先使用GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# 加载分词器
tokenizer = AutoTokenizer.from_pretrained(model_dir)

# 加载模型，并将其移动到指定设备
model = AutoModelForCausalLM.from_pretrained(model_dir).to(device)

print("模型和分词器加载完成！")

# 准备对话输入
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "你好，请介绍你自己。"}
]

# 使用分词器的模板格式化输入
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

# 编码输入文本
model_inputs = tokenizer([text], return_tensors="pt").to(device)

print("编码后的输入文本:")
print(model_inputs)

# 使用模型生成回答
# max_new_tokens 控制了模型最多能生成多少个新的Token
generated_ids = model.generate(
    model_inputs.input_ids,
    max_new_tokens=512
)

# 将生成的 Token ID 截取掉输入部分
# NOTE: 这样我们只解码模型新生成的部分 (decoder 解码器的输出包含原始输入的上下文)
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]

# 解码生成的 Token ID
response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

print("\n模型的回答:")
print(response)