# A股每日分析系统

精简定制版，每日自动推送自选股行情+AI分析到企业微信。

## 功能

- 📈 自选股实时行情（新浪财经API，免费无限制）
- 🤖 AI智能分析（OpenAI API）
- 📱 企业微信机器人推送
- ⏰ GitHub Actions自动运行（每日3次：10:00/14:00/15:30）

## 自选股

| 代码 | 名称 |
|------|------|
| 000676 | 智度股份 |
| 600030 | 中信证券 |
| 603960 | 克来机电 |
| 300059 | 东方财富 |
| 000977 | 浪潮信息 |
| 300465 | 高伟达 |
| 301366 | 一博科技 |

## 配置Secrets

在GitHub仓库 Settings → Secrets and variables → Actions 中添加：

| Secret名 | 说明 |
|----------|------|
| `OPENAI_API_KEY` | OpenAI API Key |
| `OPENAI_BASE_URL` | （可选）API基础URL，默认官方 |
| `OPENAI_MODEL` | （可选）模型名，默认gpt-4o-mini |
| `WECOM_WEBHOOK` | 企业微信机器人Webhook地址 |

## 本地运行

```bash
pip install requests
export OPENAI_API_KEY="sk-xxx"
export WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
python stock_analyzer.py
```

## 企业微信机器人配置

1. 企业微信 → 群聊 → 右上角 → 群机器人 → 添加机器人
2. 复制Webhook地址
3. 填到GitHub Secrets的 `WECOM_WEBHOOK`

## 调整推送时间

编辑 `.github/workflows/daily.yml` 中的cron表达式：

```yaml
# 格式：分 时 日 月 周
- cron: '0 10 * * 1-5'   # 周一至周五 10:00
- cron: '0 14 * * 1-5'   # 周一至周五 14:00
- cron: '30 15 * * 1-5'  # 周一至周五 15:30
```

## 添加/删除自选股

编辑 `stock_analyzer.py` 中的 `STOCKS` 列表：

```python
STOCKS = [
    ("000676", "SZ", "智度股份"),
    # 添加新股票：
    ("600519", "SH", "贵州茅台"),
]
```

- 深交所股票（0/3开头）→ `"SZ"`
- 上交所股票（6开头）→ `"SH"`
