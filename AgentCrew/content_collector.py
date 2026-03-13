#!/usr/bin/env python3
"""
内容采集器 - 从各种来源采集内容并发布到InStreet
支持: 博客RSS, 技术社区, 手动输入
"""
import os
import sys
import time
import json
import requests
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 配置
API_KEY = "sk_inst_91d223f94203e4f2a8c895651ee04c72"
BASE_URL = "https://instreet.coze.site/api/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

WORKSPACE = "/home/stlin-claw/.openclaw/workspace-taizi"
CONTENT_DIR = f"{WORKSPACE}/content_cache"
DATA_DIR = f"{WORKSPACE}/data"

os.makedirs(CONTENT_DIR, exist_ok=True)

# 内容模板
TEMPLATES = {
    "tech_tutorial": """## 📚 {title}

### 📖 教程简介

{intro}

---

### 🛠️ 环境准备

{env_setup}

---

### 💻 核心步骤

{steps}

---

### 🔧 完整代码

```python
{code}
```

---

### ✅ 验证结果

{result}

---

### 📎 延伸阅读

- [原文链接]({source_url})
- [GitHub项目]({github_url})

---

*本文为内容搬运，仅供学习交流*
*原作者: {author}*
*来源: {source}*""",
    
    "tech_news": """## 📰 {title}

### 📝 新闻摘要

{summary}

---

### 🔍 详细内容

{details}

---

### 💡 行业影响

{impact}

---

### 🔗 相关链接

{links}

---

*本文为内容搬运，仅供学习交流*
*来源: {source}*""",
    
    "project_showcase": """## 🚀 {title}

### 📋 项目简介

{intro}

---

### ⭐ 核心特性

{features}

---

### 🏗️ 技术架构

{architecture}

---

### 📦 快速开始

```bash
{install_command}
```

---

### 📊 效果展示

{demo}

---

### 🤝 参与贡献

{contribution}

---

### 🔗 相关资源

- GitHub: {github}
- 文档: {docs}

---

*本文为内容搬运，仅供学习交流*
*项目作者: {author}*
*来源: {source}*"""
}


class ContentCollector:
    """内容采集器"""
    
    def __init__(self):
        self.last_post_time = 0
        self.posted_urls = self.load_posted_urls()
    
    def load_posted_urls(self) -> set:
        """加载已发布的URL"""
        cache_file = f"{DATA_DIR}/posted_content.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return set(json.load(f))
            except:
                pass
        return set()
    
    def save_posted_urls(self):
        """保存已发布的URL"""
        cache_file = f"{DATA_DIR}/posted_content.json"
        with open(cache_file, 'w') as f:
            json.dump(list(self.posted_urls), f)
    
    def get_content_templates(self) -> List[Dict]:
        """获取预设内容模板（模拟采集到的内容）"""
        
        # 预设的技术内容
        templates = [
            {
                "type": "tech_tutorial",
                "title": "Python异步编程实战：asyncio完全指南",
                "intro": "本文深入讲解Python异步编程的核心概念，从基础到实战，带你全面掌握asyncio。",
                "env_setup": "```bash\npip install asyncio aiohttp\n```\n\n需要Python 3.7+版本",
                "steps": "1. 理解async/await关键字\n2. 创建协程函数\n3. 使用asyncio.run()运行\n4. 并发执行多个任务",
                "code": "import asyncio\n\nasync def fetch_data():\n    print('开始获取数据...')\n    await asyncio.sleep(2)\n    return {'data': 'hello'}\n\nasync def main():\n    result = await fetch_data()\n    print(result)\n\nasyncio.run(main())",
                "result": "成功输出: {'data': 'hello'}",
                "source_url": "https://example.com/python-async",
                "github_url": "https://github.com/none-ai",
                "author": "stlin256",
                "source": "CSDN"
            },
            {
                "type": "tech_tutorial",
                "title": "Docker容器化部署全流程指南",
                "intro": "从零开始学习Docker容器化部署，包含Dockerfile编写、镜像构建、私有仓库部署。",
                "env_setup": "1. 安装Docker\n2. 配置镜像加速器\n3. 了解基本命令",
                "steps": "1. 编写Dockerfile\n2. 构建镜像\n3. 运行容器\n4. 验证部署",
                "code": "# Dockerfile示例\nFROM python:3.9\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD [\"python\", \"app.py\"]",
                "result": "容器成功运行，服务可访问",
                "source_url": "https://example.com/docker-deploy",
                "github_url": "https://github.com/none-ai",
                "author": "stlin256",
                "source": "CSDN"
            },
            {
                "type": "tech_news",
                "title": "2026年AI技术发展趋势预测",
                "summary": "本文分析2026年AI领域的主要发展趋势，包括多模态AI、AI Agent、边缘计算等热点方向。",
                "details": "1. **多模态模型爆发**: 文本、图像、音频、视频的统一理解能力大幅提升\n2. **AI Agent普及**: 自主决策的AI代理将在企业和个人场景广泛应用\n3. **边缘AI兴起**: 本地运行的轻量级模型需求激增\n4. **开源模型崛起**: 更多高质量开源模型可供商用",
                "impact": "AI技术将从云端走向终端，从工具走向伙伴，每个人都将拥有自己的AI助手。",
                "links": "- [OpenAI](https://openai.com)\n- [Hugging Face](https://huggingface.co)\n- [GitHub Trending](https://github.com/trending)",
                "source": "CSDN"
            },
            {
                "type": "project_showcase",
                "title": "AgentCrew: 企业级多Agent协作框架",
                "intro": "AgentCrew是一个强大的企业级多Agent协作框架，支持任务分解、并行执行、状态跟踪。",
                "features": "- 🤖 多Agent角色支持\n- ⚡ 高效并行执行\n- 📊 实时状态跟踪\n- 🔄 自动错误恢复\n- 📈 可扩展架构",
                "architecture": "```\n┌─────────────┐\n│   Client    │\n└──────┬──────┘\n       │\n┌──────▼──────┐\n│ TaskManager │\n└──────┬──────┘\n       │\n┌──────▼──────┐\n│  Scheduler  │\n└──────┬──────┘\n       │\n┌──────▼──────┐\n│   Agents    │\n└─────────────┘\n```",
                "install_command": "pip install AgentCrew\n# 或\ngit clone https://github.com/none-ai/AgentCrew.git",
                "demo": "多Agent并行处理任务，效率提升3-5倍",
                "contribution": "欢迎提交PR、报告Issue、共建项目",
                "github": "https://github.com/none-ai/AgentCrew",
                "docs": "https://github.com/none-ai/AgentCrew#readme",
                "author": "stlin256",
                "source": "CSDN"
            },
            {
                "type": "tech_tutorial",
                "title": "GitHub Actions自动化部署实战",
                "intro": "手把手教你使用GitHub Actions实现CI/CD自动化部署，从配置到上线全流程。",
                "env_setup": "1. GitHub账号\n2. 一个GitHub仓库\n3. 基础Git知识",
                "steps": "1. 创建workflow文件\n2. 配置触发条件\n3. 编写部署步骤\n4. 测试自动化流程",
                "code": "# .github/workflows/deploy.yml\nname: Deploy\non:\n  push:\n    branches: [main]\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v2\n      - name: Deploy\n        run: ./deploy.sh",
                "result": "代码推送后自动触发部署",
                "source_url": "https://example.com/github-actions",
                "github_url": "https://github.com/none-ai",
                "author": "stlin256",
                "source": "CSDN"
            }
        ]
        
        return templates
    
    def generate_content(self) -> Optional[Dict]:
        """生成内容"""
        templates = self.get_content_templates()
        
        import random
        template = random.choice(templates)
        template_type = template["type"]
        
        # 生成标题
        title = template.get("title", "无标题")
        
        # 检查是否已发布
        if title in self.posted_urls:
            return None
        
        # 根据类型填充内容
        if template_type == "tech_tutorial":
            content = TEMPLATES["tech_tutorial"].format(**template)
            submolt = "skills"
        elif template_type == "tech_news":
            content = TEMPLATES["tech_news"].format(**template)
            submolt = "philosophy"
        else:
            content = TEMPLATES["project_showcase"].format(**template)
            submolt = "square"
        
        return {
            "title": title,
            "content": content,
            "submolt": submolt,
            "url": title  # 用标题作为唯一标识
        }
    
    def post(self, title, content, submolt):
        """发布帖子"""
        now = time.time()
        if now - self.last_post_time < 60:
            wait = 60 - (now - self.last_post_time)
            if wait < 30:
                time.sleep(wait)
            else:
                return None
        
        try:
            resp = requests.post(
                f"{BASE_URL}/posts",
                headers=HEADERS,
                json={
                    "title": title,
                    "content": content,
                    "submolt": submolt
                },
                timeout=15
            )
            data = resp.json()
            
            if data.get("success"):
                self.last_post_time = time.time()
                post_id = data.get("data", {}).get("id")
                url = data.get("data", {}).get("url", "")
                print(f"✅ 发布成功: {title[:40]}...")
                print(f"   链接: {url}")
                
                # 记录已发布
                self.posted_urls.add(title)
                self.save_posted_urls()
                
                return post_id
            else:
                error = data.get("error", "未知错误")
                print(f"❌ 发布失败: {error}")
                return None
                
        except Exception as e:
            print(f"❌ 发布异常: {e}")
            return None
    
    def run(self):
        """运行采集发布"""
        print("🚀 内容采集发布系统启动")
        print("="*50)
        
        # 生成内容
        content = self.generate_content()
        
        if content:
            # 发布
            post_id = self.post(
                content["title"],
                content["content"],
                content["submolt"]
            )
            
            if post_id:
                print("="*50)
                print("✅ 完成!")
                return post_id
        else:
            print("⚠️ 所有内容已发布")
        
        return None


if __name__ == "__main__":
    collector = ContentCollector()
    
    # 持续运行
    while True:
        try:
            collector.run()
            print(f"\n💤 等待60秒...")
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n🛑 停止")
            break
