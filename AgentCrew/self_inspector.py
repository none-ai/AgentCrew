#!/usr/bin/env python3
"""
AgentCrew 自我巡检模块
自动检查代码质量问题
"""
import os
import ast
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

WORKSPACE = "/home/stlin-claw/.openclaw/workspace-taizi"
SCRIPTS_DIR = f"{WORKSPACE}/scripts"
AGENTCREW_DIR = f"{WORKSPACE}/AgentCrew/AgentCrew"
LOG_DIR = f"{WORKSPACE}/logs"


class CodeInspector:
    """代码巡检器"""
    
    def __init__(self):
        self.issues = []
        self.stats = {
            "files_checked": 0,
            "issues_found": 0,
            "critical": 0,
            "warning": 0,
            "info": 0
        }
    
    def log_issue(self, severity: str, category: str, file: str, message: str, line: int = None):
        """记录问题"""
        issue = {
            "severity": severity,  # critical, warning, info
            "category": category,
            "file": file,
            "message": message,
            "line": line,
            "timestamp": datetime.now().isoformat()
        }
        self.issues.append(issue)
        self.stats["issues_found"] += 1
        self.stats[severity] += 1
    
    def check_python_syntax(self, file_path: str) -> bool:
        """检查 Python 语法"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.log_issue("critical", "syntax", file_path, f"语法错误: {e.msg}", e.lineno)
            return False
        except Exception as e:
            self.log_issue("warning", "parse", file_path, f"解析错误: {str(e)}")
            return False
    
    def check_imports(self, file_path: str):
        """检查导入语句"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查未使用的导入
            import re
            import_pattern = r'^import\s+(\w+)|^from\s+(\w+)\s+import'
            imports = re.findall(import_pattern, content, re.MULTILINE)
            
            # 简单检查：重复导入
            lines = content.split('\n')
            seen_imports = {}
            for i, line in enumerate(lines, 1):
                if line.strip().startswith(('import ', 'from ')):
                    if line in seen_imports:
                        self.log_issue("info", "import", file_path, 
                                     f"重复导入: {line.strip()}", i)
                    else:
                        seen_imports[line] = i
                        
        except Exception as e:
            self.log_issue("warning", "import", file_path, f"导入检查失败: {str(e)}")
    
    def check_error_handling(self, file_path: str):
        """检查错误处理"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查 bare except
            if re.search(r'except\s*:', content):
                self.log_issue("warning", "error_handling", file_path, 
                             "使用 bare except，应指定异常类型")
            
            # 检查 try without except
            try_blocks = re.findall(r'try:', content)
            except_blocks = re.findall(r'except\s+', content)
            if len(try_blocks) > len(except_blocks):
                self.log_issue("info", "error_handling", file_path,
                             f"存在 {len(try_blocks)} 个 try 但只有 {len(except_blocks)} 个 except")
                            
        except Exception as e:
            pass
    
    def check_security(self, file_path: str):
        """检查安全风险"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查硬编码密码/密钥
            if re.search(r'(password|secret|token|api_key)\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
                self.log_issue("critical", "security", file_path, 
                             "发现疑似硬编码的敏感信息")
            
            # 检查 eval/exec 使用
            if re.search(r'\b(eval|exec)\s*\(', content):
                self.log_issue("warning", "security", file_path, 
                             "使用 eval/exec 可能存在安全风险")
            
            # 检查 os.system 调用
            if re.search(r'os\.system\s*\(', content):
                self.log_issue("warning", "security", file_path, 
                             "使用 os.system 可能存在注入风险")
                            
        except Exception as e:
            pass
    
    def check_code_quality(self, file_path: str):
        """检查代码质量"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 检查过长函数 (超过 100 行)
            content = ''.join(lines)
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if hasattr(node, 'end_lineno') and node.end_lineno:
                            func_len = node.end_lineno - (node.lineno or 0)
                            if func_len > 100:
                                self.log_issue("info", "quality", file_path,
                                             f"函数 '{node.name}' 过长 ({func_len} 行)", node.lineno)
            except Exception:
                pass
            
            # 检查过长的行
            for i, line in enumerate(lines, 1):
                if len(line.rstrip()) > 120:
                    self.log_issue("info", "quality", file_path,
                                 f"行过长 ({len(line.rstrip())} 字符)", i)
                    break  # 每文件只报一次
            
            # 检查 TODO/FIXME
            if 'TODO' in content or 'FIXME' in content:
                self.log_issue("info", "quality", file_path, "存在 TODO/FIXME 注释")
            
            # 检查 print 语句 (调试代码残留)
            if re.search(r'\bprint\s*\(', content) and not file_path.endswith('_test.py'):
                # 统计 print 数量
                print_count = len(re.findall(r'\bprint\s*\(', content))
                if print_count > 5:
                    self.log_issue("warning", "quality", file_path,
                                 f"存在 {print_count} 个 print 语句，可能需要清理")
                                    
        except Exception as e:
            pass
    
    def check_shell_script(self, file_path: str):
        """检查 Shell 脚本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查 set -e
            if '#!/bin/bash' in content and 'set -e' not in content:
                self.log_issue("warning", "shell", file_path,
                             "Shell 脚本建议添加 'set -e' 错误处理")
            
            # 检查未引用的变量
            if re.search(r'\$\w+\s', content) and not re.search(r'\$\{\w+\}', content):
                self.log_issue("info", "shell", file_path,
                             "建议使用 ${var} 代替 $var 避免问题")
                            
        except Exception as e:
            pass
    
    def inspect_file(self, file_path: str):
        """巡检单个文件"""
        self.stats["files_checked"] += 1
        
        if file_path.endswith('.py'):
            self.check_python_syntax(file_path)
            self.check_imports(file_path)
            self.check_error_handling(file_path)
            self.check_security(file_path)
            self.check_code_quality(file_path)
        elif file_path.endswith('.sh'):
            self.check_shell_script(file_path)
    
    def inspect_directory(self, directory: str, pattern: str = "*.py"):
        """巡检目录"""
        path = Path(directory)
        if not path.exists():
            self.log_issue("critical", "filesystem", directory, "目录不存在")
            return
        
        for file_path in path.rglob(pattern):
            if '__pycache__' in str(file_path):
                continue
            self.inspect_file(str(file_path))
        
        # 也检查 shell 脚本
        for file_path in path.rglob("*.sh"):
            self.inspect_file(str(file_path))
    
    def get_report(self) -> Dict[str, Any]:
        """生成巡检报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "issues": self.issues
        }
    
    def save_report(self, report_path: str = None):
        """保存巡检报告"""
        if report_path is None:
            os.makedirs(LOG_DIR, exist_ok=True)
            report_path = f"{LOG_DIR}/self_inspect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.get_report()
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_path


def run_inspection(target_dir: str = None) -> Dict[str, Any]:
    """运行巡检"""
    inspector = CodeInspector()
    
    if target_dir:
        inspector.inspect_directory(target_dir)
    else:
        # 默认巡检 scripts 和 AgentCrew 核心代码
        inspector.inspect_directory(SCRIPTS_DIR)
        inspector.inspect_directory(AGENTCREW_DIR)
    
    return inspector.get_report()


if __name__ == "__main__":
    import sys
    
    target = sys.argv[1] if len(sys.argv) > 1 else None
    report = run_inspection(target)
    
    print(f"📊 巡检完成: 检查了 {report['stats']['files_checked']} 个文件")
    print(f"   🔴 严重: {report['stats']['critical']}")
    print(f"   🟡 警告: {report['stats']['warning']}")
    print(f"   🔵 信息: {report['stats']['info']}")
    
    if report['stats']['issues_found'] > 0:
        print(f"\n发现问题详情已保存")
