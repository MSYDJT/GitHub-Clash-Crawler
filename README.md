# GitHub Clash订阅链接爬取工具

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

一款智能爬取GitHub上Clash订阅链接的图形界面工具，模拟真实用户行为绕过限制，高效获取有效订阅配置。

![应用截图](assets/app_screenshot.png)

## 功能特点

- 🕵️‍♂️ **智能爬取引擎**：模拟真实用户浏览行为，避免被封禁
- 🔍 **多关键词搜索**：使用8个相关关键词组合搜索
- 📂 **深度仓库探索**：递归搜索仓库中的子目录和文件
- ✅ **内容验证**：自动检测有效的Clash配置文件
- 🖥️ **用户友好界面**：图形化操作，实时结果显示
- 📊 **详细统计**：记录爬取过程的各项指标

## 安装与运行

### 前置要求
- Python 3.8+
- Git (可选)

### 安装步骤
1. 克隆仓库：
```bash
git clone https://github.com/MSYDJT/GitHub-Clash-Crawler.git
cd GitHub-Clash-Crawler
```
2. 克隆仓库：
```bash
pip install -r requirements.txt
```
3.运行程序：
```bash
python github_clash_crawler.py
```
使用指南

设置参数：
调整"搜索页数"（建议3-5页）
设置"最大仓库数"（建议10-20个）
开始爬取：
点击"开始爬取"按钮
等待爬取完成（可能需要5-15分钟）

操作结果：
选择链接后使用"复制"、"打开"或"测试"按钮
点击"保存结果"将链接保存到文件
查看"统计信息"了解爬取详情

注意事项

合法使用：
遵守GitHub的服务条款
尊重robots.txt规则
不要过度请求，避免给GitHub服务器造成负担

爬取策略：
默认设置已优化避免被封禁
如遇验证页面，爬取会自动跳过
建议每次爬取间隔至少30分钟

贡献指南
欢迎贡献！请按以下步骤操作：
Fork项目仓库
创建特性分支 (git checkout -b feature/AmazingFeature)
提交更改 (git commit -m 'Add some AmazingFeature')
推送到分支 (git push origin feature/AmazingFeature)
创建Pull Request

许可证
本项目采用 MIT 许可证

免责声明
本工具仅用于技术研究和学习目的。使用者应遵守相关法律法规，自行承担使用风险。开发者不对任何滥用行为负责。
