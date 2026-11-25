# Book → Skill（网页原型）

把 PDF / EPUB / DOCX / TXT / Markdown 电子书转换成 Agent Skill：`SKILL.md`、主题知识地图、术语表、方法模式、速查表。

## 在线部署（推荐 Streamlit Community Cloud）

1. 将本项目文件上传到你自己的 GitHub 仓库。
2. 打开 https://share.streamlit.io/ 并用 GitHub 登录。
3. 选择仓库、分支和 `app.py`，点击 Deploy。
4. 部署完成后，浏览器即可打开网页；电脑、平板和手机都能使用。

## 本地运行

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 使用

- 在左侧填写你自己的 OpenAI 兼容 API Key、模型名和可选 Base URL。
- 上传 PDF、EPUB、DOCX、TXT 或 MD。
- 选择语言和深度，点击“开始转换”。
- 检查生成内容，下载完整 ZIP。

## 注意事项

- 当前是可运行的 MVP 原型，不是对上游项目的完整复刻。
- 模型 API 会收到提取出的书籍文本；不要上传无权处理或含敏感信息的文件。
- 本版不保存上传文件到服务器磁盘，但部署平台和模型服务商仍有各自的数据处理政策。
- 扫描版 PDF 需要 OCR，本版暂不含 OCR。
- 为避免一次请求过大，默认限制发送文本长度；长书建议按章节拆分处理。
- 请只处理你有权使用的书籍，并将生成 Skill 用于个人学习或许可允许的用途。
