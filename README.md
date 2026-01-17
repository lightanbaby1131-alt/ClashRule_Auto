# ClashRule_Auto  
一个自动化、可维护、每日更新的 Clash / OpenClash 规则集项目

---

## 📌 项目简介  
**ClashRule_Auto** 是一个基于 GitHub Actions 自动化构建的规则仓库，专注于生成 **Clash / OpenClash 可直接识别的 `.list` 规则文件**。  
项目每天会在 **北京时间 01:10** 自动运行，通过脚本从多个上游规则源拉取最新内容，进行过滤、去重、排除冲突、格式化分类，并最终生成高质量的 `.list` 规则文件。

目标是打造一个 **稳定、干净、无误杀、可长期维护** 的规则生态，让用户无需手动更新即可获得最新的广告过滤、隐私保护、程序拦截等规则。

---

## ✨ 项目特点

### 🔄 自动每日更新  
- 使用 GitHub Actions 定时任务  
- 每天自动拉取上游规则  
- 自动生成 `.list` 文件并提交到仓库  
- 无需人工干预，始终保持最新状态  

### 🧹 智能去重与排除  
- 自动去除重复规则  
- 支持排除指定规则源（如 BanAD、BanEasyPrivacy 等）  
- 避免规则冲突、重复匹配、误杀等问题  

### 🧩 完全兼容 Clash / OpenClash  
生成的 `.list` 文件严格遵循 Clash 规则格式，包括：  
- `DOMAIN-SUFFIX`  
- `DOMAIN`  
- `DOMAIN-KEYWORD`  
- `DOMAIN-REGEX`  

确保可直接用于：  
- OpenClash  
- Clash.Meta  
- Clash Premium  
- 以及其他兼容 Clash 规则的客户端  

### 🗂️ 自动分类与格式化  
脚本会自动将规则按类型分组，提升可读性：  
- DOMAIN-SUFFIX  
- DOMAIN  
- DOMAIN-KEYWORD  
- DOMAIN-REGEX  

并在文件头部自动生成：  
- 更新时间（北京时间）  
- 上游规则来源  
- 上游规则更新时间  
- 排除源信息  
- 最终规则数量统计  

### 🧪 安全性优先  
- 严格过滤非域名类规则  
- 避免误杀常见服务  
- 保留必要的广告/隐私拦截能力  
- 适合长期稳定使用  

---

## 📁 目录结构

