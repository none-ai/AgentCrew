#!/usr/bin/env python3
"""
AgentCrew 自我迭代模块
自动修复发现的问题
"""
import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 支持直接运行和模块导入
try:
    from .self_inspector import CodeInspector, run_inspection
except ImportError:
    from self_inspector import CodeInspector, run_inspection

WORKSPACE = "/home/stlin-claw/.openclaw/workspace-taizi"
SCRIPTS_DIR = f"{WORKSPACE}/scripts"
AGENTCREW_DIR = f"{WORKSPACE}/AgentCrew/AgentCrew"
LOG_DIR = f"{WORKSPACE}/logs"


class AutoFixer:
    """自动修复器"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.fixes_applied = []
        self.fixes_failed = []
        self.auto_fixable_rules = {
            "syntax": self.fix_syntax_errors,
            "import": self.fix_import_issues,
            "quality": self.fix_quality_issues,
            "shell": self.fix_shell_issues,
        }
    
    def fix_syntax_errors(self, issue: Dict) -> bool:
        """修复语法错误"""
        # 语法错误需要手动处理，这里只记录
        return False
    
    def fix_import_issues(self, issue: Dict) -> bool:
        """修复导入问题"""
        # 重复导入可以移除
        if "重复导入" in issue["message"]:
            # 简单处理：不做自动修复
            return False
        return False
    
    def fix_quality_issues(self, issue: Dict) -> bool:
        """修复代码质量问题"""
        file_path = issue["file"]
        message = issue["message"]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 处理过长的行
            if "行过长" in message:
                lines = content.split('\n')
                fixed_lines = []
                for line in lines:
                    if len(line.rstrip()) > 120:
                        # 简单换行处理
                        if '=' in line and len(line) <= 150:
                            # 中等长度，尝试在 = 处换行
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                indent = len(line) - len(line.lstrip())
                                prefix = ' ' * indent
                                fixed_lines.append(f"{parts[0].strip()} = \\")
                                fixed_lines.append(f"{prefix}{parts[1].strip()}")
                                continue
                    fixed_lines.append(line)
                
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(fixed_lines))
                    self.fixes_applied.append({
                        "file": file_path,
                        "fix": "行过长已格式化"
                    })
                return True
            
            # 移除调试 print 语句（如果是大量的话）
            if "print 语句" in message:
                # 统计 print 数量
                print_count = len(re.findall(r'\bprint\s*\(', content))
                if print_count > 10:
                    # 不自动删除 print 语句，建议手动审查
                    pass
                return False
            
            return False
            
        except Exception as e:
            self.fixes_failed.append({
                "file": file_path,
                "error": str(e)
            })
            return False
    
    def fix_shell_issues(self, issue: Dict) -> bool:
        """修复 Shell 脚本问题"""
        file_path = issue["file"]
        message = issue["message"]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "set -e" in message:
                # 添加 set -e
                lines = content.split('\n')
                new_lines = []
                for i, line in enumerate(lines):
                    if i == 0 and line.startswith('#!'):
                        new_lines.append(line)
                        new_lines.append('set -e')
                    else:
                        new_lines.append(line)
                
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines))
                    self.fixes_applied.append({
                        "file": file_path,
                        "fix": "添加 set -e"
                    })
                return True
            
            return False
            
        except Exception as e:
            self.fixes_failed.append({
                "file": file_path,
                "error": str(e)
            })
            return False
    
    def try_fix_issue(self, issue: Dict) -> bool:
        """尝试修复单个问题"""
        category = issue.get("category", "")
        rule = self.auto_fixable_rules.get(category)
        
        if rule:
            return rule(issue)
        return False
    
    def apply_fixes(self, issues: List[Dict]) -> Dict[str, Any]:
        """应用自动修复"""
        auto_fixable = ["quality", "shell"]
        
        for issue in issues:
            if issue["severity"] in ["critical", "warning"]:
                category = issue.get("category", "")
                if category in auto_fixable:
                    if self.try_fix_issue(issue):
                        pass  # fix applied via function
        
        return {
            "dry_run": self.dry_run,
            "fixes_applied": self.fixes_applied,
            "fixes_failed": self.fixes_failed,
            "total_issues": len(issues),
            "auto_fixable_attempted": len([i for i in issues if i.get("category") in auto_fixable])
        }


def run_auto_fix(dry_run: bool = True) -> Dict[str, Any]:
    """运行自动修复"""
    print("🔍 正在巡检...")
    report = run_inspection()
    
    fixer = AutoFixer(dry_run=dry_run)
    result = fixer.apply_fixes(report["issues"])
    
    return result


def suggest_improvements(issues: List[Dict]) -> List[str]:
    """生成改进建议（需要人工审查的）"""
    suggestions = []
    by_file = {}
    
    for issue in issues:
        file = issue.get("file", "unknown")
        if file not in by_file:
            by_file[file] = []
        by_file[file].append(issue)
    
    for file, file_issues in by_file.items():
        file_suggestions = []
        for issue in file_issues:
            if issue["severity"] == "critical":
                if issue["category"] == "security" and "硬编码" in issue["message"]:
                    file_suggestions.append("⚠️ 需人工处理：移除硬编码的敏感信息")
                elif issue["category"] == "syntax":
                    file_suggestions.append(f"⚠️ 需人工处理：语法错误 line {issue.get('line')}")
        
        if file_suggestions:
            suggestions.append(f"\n📁 {file}:")
            suggestions.extend(file_suggestions)
    
    return suggestions


if __name__ == "__main__":
    import sys
    
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    
    print(f"🔧 自动修复模式: {'模拟' if dry_run else '实际执行'}")
    result = run_auto_fix(dry_run=dry_run)
    
    print(f"\n📊 修复结果:")
    print(f"   总问题数: {result['total_issues']}")
    print(f"   已尝试自动修复: {result['auto_fixable_attempted']}")
    print(f"   修复成功: {len(result['fixes_applied'])}")
    print(f"   修复失败: {len(result['fixes_failed'])}")
    
    if result['fixes_applied']:
        print("\n✅ 已修复:")
        for fix in result['fixes_applied']:
            print(f"   {fix['file']}: {fix['fix']}")
