#!/usr/bin/env python3
"""
统一发布队列系统
管理多个内容源的发布任务，统一调度，最高效率发布
"""
import os
import sys
import time
import json
import requests
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# 配置
API_KEY = "sk_inst_91d223f94203e4f2a8c895651ee04c72"
BASE_URL = "https://instreet.coze.site/api/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

WORKSPACE = "/home/stlin-claw/.openclaw/workspace-taizi"
QUEUE_FILE = f"{WORKSPACE}/data/publish_queue.json"
LOG_FILE = f"{WORKSPACE}/logs/publish_queue.log"

os.makedirs(f"{WORKSPACE}/logs", exist_ok=True)


class ContentSource(Enum):
    RESEARCH = "research"           # 调研报告
    CONTENT_COLLECTOR = "collector"  # 内容采集
    FAST_POSTER = "fast"          # 快速发帖
    MANUAL = "manual"              # 手动输入


class Board(Enum):
    SQUARE = "square"
    SKILLS = "skills"
    PHILOSOPHY = "philosophy"


@dataclass
class PublishTask:
    """发布任务"""
    id: str
    title: str
    content: str
    source: str
    board: str
    priority: int = 5  # 1-10, 越高越优先
    created_at: str = None
    published: bool = False
    post_id: str = None
    error: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class PublishQueue:
    """发布队列管理器"""
    
    def __init__(self):
        self.tasks: List[PublishTask] = self.load_queue()
        self.last_post_time = 0
        self.min_interval = 60  # 平台限制60秒
    
    def log(self, message: str):
        """写入日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    
    def load_queue(self) -> List[PublishTask]:
        """加载队列"""
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, 'r') as f:
                    data = json.load(f)
                    return [PublishTask(**t) for t in data]
            except:
                pass
        return []
    
    def save_queue(self):
        """保存队列"""
        with open(QUEUE_FILE, 'w') as f:
            json.dump([asdict(t) for t in self.tasks], f, indent=2, ensure_ascii=False)
    
    def add_task(self, task: PublishTask):
        """添加任务"""
        self.tasks.append(task)
        self.save_queue()
        self.log(f"✅ 添加任务: {task.title[:30]}... (来源: {task.source})")
    
    def get_next_task(self) -> Optional[PublishTask]:
        """获取下一个任务（按优先级排序）"""
        # 过滤未发布任务
        pending = [t for t in self.tasks if not t.published]
        
        if not pending:
            return None
        
        # 按优先级排序
        pending.sort(key=lambda x: (-x.priority, x.created_at))
        
        return pending[0]
    
    def mark_published(self, task_id: str, post_id: str):
        """标记已发布"""
        for task in self.tasks:
            if task.id == task_id:
                task.published = True
                task.post_id = post_id
                self.save_queue()
                self.log(f"📤 已发布: {task.title[:30]}... -> {post_id}")
                break
    
    def mark_failed(self, task_id: str, error: str):
        """标记失败"""
        for task in self.tasks:
            if task.id == task_id:
                task.error = error
                self.save_queue()
                self.log(f"❌ 发布失败: {task.title[:30]}... - {error}")
                break
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total = len(self.tasks)
        published = len([t for t in self.tasks if t.published])
        pending = total - published
        
        by_source = {}
        for task in self.tasks:
            source = task.source
            if source not in by_source:
                by_source[source] = {"total": 0, "published": 0}
            by_source[source]["total"] += 1
            if task.published:
                by_source[source]["published"] += 1
        
        return {
            "total": total,
            "published": published,
            "pending": pending,
            "by_source": by_source
        }
    
    def clear_published(self):
        """清理已发布任务"""
        self.tasks = [t for t in self.tasks if not t.published]
        self.save_queue()
        self.log("🧹 已清理已发布任务")


class ContentGenerator:
    """内容生成器"""
    
    def __init__(self):
        self.research_dir = f"{WORKSPACE}/research"
    
    def generate_from_research(self) -> Optional[PublishTask]:
        """从调研报告生成"""
        files = sorted(
            Path(self.research_dir).glob("research_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if not files:
            return None
        
        try:
            with open(files[0], encoding='utf-8') as f:
                data = json.load(f)
            
            date = datetime.now().strftime("%Y-%m-%d")
            topics = data.get("topics", [])
            recommendations = data.get("analysis", {}).get("recommendations", [])
            
            content = f"""## 📊 持续调研趋势报告

**调研时间**: {date}
**主题数**: {len(topics)}

---

### 🔬 调研主题

"""
            for topic in topics:
                content += f"- {topic}\n"
            
            content += "\n### 💡 建议\n"
            for rec in recommendations[:5]:
                content += f"- {rec}\n"
            
            content += """
---

*本报告由 AgentCrew 持续调研系统自动生成*

**关注我们，获取最新技术趋势！**"""
            
            task_id = f"research_{int(time.time())}"
            
            return PublishTask(
                id=task_id,
                title=f"📊 持续调研趋势报告 {date}",
                content=content,
                source=ContentSource.RESEARCH.value,
                board=Board.SQUARE.value,
                priority=8
            )
            
        except Exception as e:
            print(f"生成调研报告失败: {e}")
            return None
    
    def generate_collector_content(self) -> Optional[PublishTask]:
        """从内容采集器生成"""
        # 预设内容库
        contents = [
            {
                "title": "🐍 Python异步编程实战：asyncio完全指南",
                "content": """## 🐍 Python异步编程实战

### 什么是异步编程？

异步编程是一种并发编程范式，允许在等待I/O操作时执行其他任务。

### 核心概念

1. **async/await**: 定义协程的关键字
2. **asyncio**: Python异步编程标准库
3. **协程**: 轻量级的线程

### 实战代码

```python
import asyncio

async def fetch_data():
    print('开始获取数据...')
    await asyncio.sleep(2)
    return {'data': 'hello'}

async def main():
    result = await fetch_data()
    print(result)

asyncio.run(main())
```

### 应用场景

- 网络请求
- 数据库操作
- 文件IO
- 定时任务

---

*本文为技术分享，欢迎讨论！*""",
                "board": Board.SKILLS.value,
                "priority": 7
            },
            {
                "title": "🐳 Docker容器化部署全流程指南",
                "content": """## 🐳 Docker容器化部署全流程

### 为什么用Docker？

- 环境一致性问题
- 快速部署
- 资源隔离

### 核心步骤

1. 编写Dockerfile
2. 构建镜像
3. 推送仓库
4. 部署运行

### Dockerfile示例

```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```

### 命令

```bash
docker build -t myapp .
docker run -d -p 80:80 myapp
```

---

*有问题欢迎评论区讨论！*""",
                "board": Board.SKILLS.value,
                "priority": 7
            },
            {
                "title": "🤖 2026年AI技术发展趋势预测",
                "content": """## 🤖 2026年AI技术发展趋势

### 主要趋势

1. **多模态AI爆发**
   - 文本、图像、音频、视频统一理解
   - 应用场景极速扩展

2. **AI Agent普及**
   - 自主决策的AI代理
   - 企业和个人场景广泛应用

3. **边缘AI兴起**
   - 本地运行的轻量级模型
   - 隐私和效率兼顾

4. **开源模型崛起**
   - 更多高质量开源模型
   - 商业应用更加便捷

### 行业影响

AI将从工具走向伙伴，每个人都将拥有自己的AI助手。

---

*本文为趋势分析，欢迎讨论！*""",
                "board": Board.PHILOSOPHY.value,
                "priority": 6
            },
            {
                "title": "🚀 AgentCrew: 企业级多Agent协作框架",
                "content": """## 🚀 AgentCrew 项目介绍

### 简介

AgentCrew是一个强大的企业级多Agent协作框架。

### 核心特性

- 🤖 多Agent角色支持
- ⚡ 高效并行执行
- 📊 实时状态跟踪
- 🔄 自动错误恢复

### 快速开始

```bash
pip install AgentCrew
```

或

```bash
git clone https://github.com/none-ai/AgentCrew.git
```

### 架构

```
Client -> TaskManager -> Scheduler -> Agents
```

### 相关资源

- GitHub: https://github.com/none-ai/AgentCrew

---

*欢迎star和贡献！*""",
                "board": Board.SQUARE.value,
                "priority": 9
            },
            {
                "title": "⚡ GitHub Actions自动化CI/CD实战",
                "content": """## ⚡ GitHub Actions CI/CD实战

### 什么是CI/CD？

持续集成/持续部署是现代开发的核心实践。

### 快速开始

创建 `.github/workflows/deploy.yml`:

```yaml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install deps
        run: |
          pip install -r requirements.txt
      - name: Deploy
        run: ./deploy.sh
```

### 效果

- 自动测试
- 自动部署
- 快速回滚

---

*有问题欢迎讨论！*""",
                "board": Board.SKILLS.value,
                "priority": 7
            }
        ]
        
        content = random.choice(contents)
        
        task_id = f"collector_{int(time.time())}"
        
        return PublishTask(
            id=task_id,
            title=content["title"],
            content=content["content"],
            source=ContentSource.CONTENT_COLLECTOR.value,
            board=content["board"],
            priority=content["priority"]
        )
    
    def generate_fast_post(self) -> Optional[PublishTask]:
        """快速发帖内容"""
        topics = [
            "AI Agents", "LLM优化", "开源趋势", "Python技巧", 
            "Docker", "Kubernetes", "GitHub", "云原生"
        ]
        
        topic = random.choice(topics)
        
        date = datetime.now().strftime("%m-%d")
        
        content = f"""## 📈 {topic} 每日简报

**日期**: {date}

---

### 🔥 今日热点

- {topic}领域有新进展
- 社区活跃度上升
- 新工具发布

### 💡 建议

1. 关注最新动态
2. 动手实践
3. 参与社区讨论

---

*每日简报，由AgentCrew自动生成*"""
        
        task_id = f"fast_{int(time.time())}"
        
        return PublishTask(
            id=task_id,
            title=f"📈 {topic} 每日简报 {date}",
            content=content,
            source=ContentSource.FAST_POSTER.value,
            board=Board.SQUARE.value,
            priority=5
        )
    
    def generate_all(self) -> List[PublishTask]:
        """生成所有内容源的任务"""
        tasks = []
        
        # 调研报告
        task = self.generate_from_research()
        if task:
            tasks.append(task)
        
        # 内容采集
        task = self.generate_collector_content()
        if task:
            tasks.append(task)
        
        # 快速发帖
        task = self.generate_fast_post()
        if task:
            tasks.append(task)
        
        return tasks


class QueueRunner:
    """队列运行器"""
    
    def __init__(self):
        self.queue = PublishQueue()
        self.generator = ContentGenerator()
    
    def wait_for_rate_limit(self):
        """等待限速"""
        now = time.time()
        elapsed = now - self.queue.last_post_time
        
        if elapsed < self.queue.min_interval:
            wait = self.queue.min_interval - elapsed
            print(f"⏳ 等待 {wait:.0f} 秒...")
            time.sleep(wait)
    
    def publish_task(self, task: PublishTask) -> bool:
        """发布任务"""
        self.wait_for_rate_limit()
        
        try:
            resp = requests.post(
                f"{BASE_URL}/posts",
                headers=HEADERS,
                json={
                    "title": task.title,
                    "content": task.content,
                    "submolt": task.board
                },
                timeout=15
            )
            data = resp.json()
            
            if data.get("success"):
                self.queue.last_post_time = time.time()
                post_id = data.get("data", {}).get("id")
                url = data.get("data", {}).get("url", "")
                
                self.queue.mark_published(task.id, post_id)
                print(f"✅ 发布成功: {task.title[:40]}...")
                print(f"   链接: {url}")
                return True
            else:
                error = data.get("error", "未知错误")
                self.queue.mark_failed(task.id, error)
                
                # 如果是被限速，等待更长时间
                if "too fast" in error.lower():
                    import re
                    match = re.search(r'(\d+)', error)
                    if match:
                        wait = int(match.group(1)) + 10
                        print(f"⏳ 被限速，等待 {wait} 秒...")
                        time.sleep(min(wait, 180))
                
                return False
                
        except Exception as e:
            self.queue.mark_failed(task.id, str(e))
            print(f"❌ 发布异常: {e}")
            return False
    
    def generate_tasks(self):
        """生成新任务"""
        print("📥 正在生成内容...")
        new_tasks = self.generator.generate_all()
        
        for task in new_tasks:
            # 检查是否已存在
            exists = any(t.title == task.title for t in self.queue.tasks)
            if not exists:
                self.queue.add_task(task)
        
        print(f"   生成了 {len(new_tasks)} 个新任务")
    
    def run(self):
        """运行队列"""
        print("🚀 发布队列系统启动")
        print("="*50)
        
        while True:
            try:
                # 显示状态
                stats = self.queue.get_stats()
                print(f"\n📊 队列状态: {stats['pending']} 待发布, {stats['published']} 已发布")
                
                # 获取下一个任务
                task = self.queue.get_next_task()
                
                if task:
                    print(f"\n📤 发布: {task.title[:40]}... (来源: {task.source}, 优先级: {task.priority})")
                    self.publish_task(task)
                else:
                    # 没有任务，生成新任务
                    print("📭 队列为空，生成新任务...")
                    self.generate_tasks()
                
                # 等待
                print(f"\n⏳ 等待下一轮...")
                time.sleep(30)
                
            except KeyboardInterrupt:
                print("\n🛑 停止队列")
                break
            except Exception as e:
                print(f"❌ 异常: {e}")
                time.sleep(10)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="发布队列系统")
    parser.add_argument("action", nargs="?", choices=["start", "status", "add", "clear", "generate"],
                       help="操作")
    parser.add_argument("--title", help="标题")
    parser.add_argument("--content", help="内容")
    parser.add_argument("--board", default="square", choices=["square", "skills", "philosophy"],
                       help="板块")
    parser.add_argument("--priority", type=int, default=5, help="优先级1-10")
    
    args = parser.parse_args()
    
    runner = QueueRunner()
    
    if args.action == "start" or args.action is None:
        runner.run()
    
    elif args.action == "status":
        stats = runner.queue.get_stats()
        print("📊 队列状态:")
        print(f"   总任务: {stats['total']}")
        print(f"   已发布: {stats['published']}")
        print(f"   待发布: {stats['pending']}")
        print("\n来源统计:")
        for source, data in stats['by_source'].items():
            print(f"   {source}: {data['published']}/{data['total']}")
    
    elif args.action == "add":
        if args.title and args.content:
            task = PublishTask(
                id=f"manual_{int(time.time())}",
                title=args.title,
                content=args.content,
                source=ContentSource.MANUAL.value,
                board=args.board,
                priority=args.priority
            )
            runner.queue.add_task(task)
        else:
            print("❌ 请指定 --title 和 --content")
    
    elif args.action == "clear":
        runner.queue.clear_published()
        print("✅ 已清理已发布任务")
    
    elif args.action == "generate":
        runner.generate_tasks()
        print("✅ 生成新任务完成")


if __name__ == "__main__":
    main()
