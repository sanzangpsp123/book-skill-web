import io, os, re, json, zipfile
from pathlib import Path
import streamlit as st
from pypdf import PdfReader
from docx import Document
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup
from openai import OpenAI

st.set_page_config(page_title="Book → Skill", page_icon="📚", layout="wide")
st.title("📚 Book → Skill")
st.caption("把电子书整理成可复用的 AI Agent Skill（SKILL.md + 章节知识库）")

with st.sidebar:
    st.header("模型设置")
    st.info("上传内容会发送给你选择的模型服务商进行分析。请只处理你有权使用的书籍，并避免上传敏感资料。")
    api_key = st.text_input("API Key", type="password", help="使用你自己的模型服务商 API Key。")
    base_url = st.text_input("兼容 OpenAI 的 API 地址（可选）", value="")
    model = st.text_input("模型名称", value="gpt-4o-mini")
    st.caption("API Key 只在当前运行会话中使用，不写入生成文件。")

def extract_file(upload):
    name = upload.name.lower()
    data = upload.getvalue()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    if name.endswith(".epub"):
        book = epub.read_epub(io.BytesIO(data))
        parts = []
        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                parts.append(soup.get_text(" ", strip=True))
        return "\n\n".join(parts)
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    raise ValueError("暂不支持该格式。请上传 PDF、EPUB、DOCX、TXT 或 MD。")

def slugify(s):
    s = re.sub(r"[^\w\-]+", "-", s.strip().lower(), flags=re.UNICODE)
    return re.sub(r"-+", "-", s).strip("-")[:60] or "book-skill"

def ask_model(client, model_name, prompt, text):
    response = client.chat.completions.create(
        model=model_name,
        temperature=0.2,
        messages=[
            {"role":"system","content":"你是一名严谨的知识工程师。只根据用户提供的书籍文本提炼知识。不得大段复制原文；用自己的话总结。若材料不足，明确标注未知，不得编造。输出必须遵循用户指定格式。"},
            {"role":"user","content":prompt + "\n\n--- BOOK TEXT ---\n" + text}
        ]
    )
    return response.choices[0].message.content or ""

st.subheader("1. 上传书籍")
uploaded = st.file_uploader("选择电子书文件", type=["pdf","epub","docx","txt","md"])
col1, col2 = st.columns(2)
with col1:
    skill_title = st.text_input("Skill 名称", value=(Path(uploaded.name).stem if uploaded else "我的读书技能"))
with col2:
    language = st.selectbox("输出语言", ["简体中文", "English", "中英双语"])
depth = st.select_slider("提炼深度", options=["精简", "标准", "深入"], value="标准")
max_chars = st.selectbox("发送给模型的文本上限", [30000, 60000, 100000, 160000], index=1)

if uploaded:
    try:
        book_text = extract_file(uploaded)
        book_text = re.sub(r"\n{3,}", "\n\n", book_text).strip()
        st.success(f"提取完成：约 {len(book_text):,} 个字符")
        if not book_text:
            st.warning("没有提取到文字。若这是扫描版 PDF，需要先进行 OCR 文字识别。")
        elif len(book_text) > max_chars:
            st.warning(f"文本超过本次设置的上限，将截取前 {max_chars:,} 个字符。建议先拆分章节处理，避免遗漏后半部分。")
        with st.expander("预览提取文本"):
            st.text(book_text[:5000])
    except Exception as e:
        st.error(f"读取失败：{e}")
        book_text = ""
else:
    book_text = ""

st.subheader("2. 生成 Skill")
st.write("生成内容包括核心 Skill、章节索引、术语表、方法模式和速查表。")
if st.button("✨ 开始转换", type="primary", disabled=not (uploaded and book_text and api_key and skill_title.strip())):
    try:
        client = OpenAI(api_key=api_key, base_url=base_url.strip() or None)
        content = book_text[:max_chars]
        lang = language
        depth_desc = {"精简":"只保留最重要的概念和可执行规则","标准":"覆盖主要框架、方法、例子和适用条件","深入":"尽可能完整地提炼框架、步骤、决策规则、边界和反例"}[depth]
        with st.spinner("模型正在提炼知识，请稍候……"):
            plan_prompt = f"""请用{lang}为这本书生成结构化知识提纲。{depth_desc}
输出 Markdown，包含：书籍主题、章节/主题划分（若无法确定真实章节就按主题划分并注明）、核心框架、关键术语、可执行方法、适用边界、常见误区。不要照抄原文。"""
            outline = ask_model(client, model, plan_prompt, content)
            skill_prompt = f"""根据书籍文本和提纲，生成一个可供 AI Agent 使用的完整 SKILL.md。
Skill 名称：{skill_title}；语言：{lang}；深度：{depth}。
必须包含 YAML frontmatter（name、description）、何时调用、核心原则、工作流程、决策规则、常见错误、引用/证据规则，以及“详细知识请按需读取 references/ 下文件”。
不要声称掌握书中没有出现的信息。不要大段复制原文。
提纲如下：
{outline}"""
            skill_md = ask_model(client, model, skill_prompt, content)
            refs = {}
            for filename, purpose in [
                ("chapters-and-frameworks.md","章节/主题知识地图与核心框架"),
                ("glossary.md","关键术语及简明定义"),
                ("patterns.md","方法、步骤、决策规则、适用条件和反例"),
                ("cheatsheet.md","快速查阅表与行动清单"),
            ]:
                p = f"""请为书籍《{skill_title}》生成 {filename}，语言为{lang}，深度为{depth}。
用途：{purpose}。请用自己的话总结，避免长段原文复制；每项尽量注明来自哪个章节/主题。材料不支持的内容标为“原文未明确”。"""
                refs[filename] = ask_model(client, model, p, content)
        st.session_state["generated"] = {
            "skill": skill_md, "outline": outline, "refs": refs,
            "slug": slugify(skill_title), "title": skill_title
        }
        st.success("转换完成！请检查内容后再下载。")
    except Exception as e:
        st.error(f"生成失败：{e}")

if "generated" in st.session_state:
    g = st.session_state["generated"]
    st.subheader("3. 检查并导出")
    tabs = st.tabs(["SKILL.md", "知识提纲", "章节与框架", "术语表", "方法模式", "速查表"])
    vals = [g["skill"], g["outline"], g["refs"]["chapters-and-frameworks.md"],
            g["refs"]["glossary.md"], g["refs"]["patterns.md"], g["refs"]["cheatsheet.md"]]
    names = ["SKILL.md","outline.md","chapters-and-frameworks.md","glossary.md","patterns.md","cheatsheet.md"]
    for tab, val, nm in zip(tabs, vals, names):
        with tab:
            st.code(val, language="markdown")
            st.download_button(f"下载 {nm}", val, file_name=nm, mime="text/markdown", key="dl_"+nm)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{g['slug']}/SKILL.md", g["skill"])
        z.writestr(f"{g['slug']}/outline.md", g["outline"])
        for nm, val in g["refs"].items():
            z.writestr(f"{g['slug']}/references/{nm}", val)
        readme = f"""# {g['title']} — AI Skill

本目录由 Book → Skill 生成。先阅读 `SKILL.md`，再按需读取 `references/` 中的知识文件。

请人工核对模型生成内容，尤其是章节归属、事实、数字和引用。生成结果是学习辅助材料，不替代原书。
"""
        z.writestr(f"{g['slug']}/README.md", readme)
    st.download_button("📦 下载完整 Skill ZIP", buf.getvalue(), file_name=f"{g['slug']}.zip", mime="application/zip", type="primary")

st.divider()
st.caption("隐私提示：本工具当前为单用户原型，不保存上传文件到服务器磁盘；但文本会发送到你配置的模型 API。扫描版 PDF 暂不支持 OCR。")
