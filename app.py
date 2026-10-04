import tempfile
import time
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import ebooklib
from ebooklib import epub
import streamlit as st

st.set_page_config(
    page_title="EPUB Book Translator", page_icon="📖", layout="centered"
)

st.title("📖 เครื่องมือแปลหนังสือ EPUB (อังกฤษ ➡ ไทย)")
st.write(
    "อัปโหลดไฟล์หนังสือของคุณ เลือกรูปแบบการแปล ระบบจะทำการแปลให้อัตโนมัติ"
    " (ฟรี ไม่ต้องใช้ API Key)"
)

# กำหนดตัวแปร Session State เพื่อจำสถานะระหว่างกดปุ่ม
if "translated_file_path" not in st.session_state:
  st.session_state.translated_file_path = None
if "is_translating" not in st.session_state:
  st.session_state.is_translating = False

translation_mode = st.radio(
    "เลือกโหมดการแปลภาษา:",
    (
        "📚 แบบสองภาษา (สลับย่อหน้า: อังกฤษบน - ไทยล่าง)",
        "🇹🇭 เฉพาะภาษาไทยล้วน (แปลธรรมชาติ อ่านลื่นไหล)",
    ),
    key="mode_radio",
)

uploaded_file = st.file_uploader(
    "เลือกไฟล์หนังสือรูปแบบ .epub", type=["epub"]
)


def safe_translate(text, mode_bilingual=True):
  if not text.strip() or len(text.strip()) < 3:
    return text

  translator = GoogleTranslator(source="en", target="th")
  if len(text) > 3000:
    chunks = [text[i : i + 3000] for i in range(0, len(text), 3000)]
  else:
    chunks = [text]

  translated_chunks = []
  for chunk in chunks:
    success = False
    for attempt in range(3):
      try:
        res = translator.translate(chunk)
        if res:
          translated_chunks.append(res)
          success = True
          break
      except Exception:
        time.sleep(1)
    if not success:
      translated_chunks.append(chunk)
    time.sleep(0.3)

  translated_text = "".join(translated_chunks)
  if mode_bilingual:
    return f"{text}\n\n{translated_text}"
  else:
    return translated_text


if uploaded_file is not None:
  st.info(f"📁 ไฟล์ที่เลือก: **{uploaded_file.name}**")

  # ปุ่มเริ่มแปล
  if st.button("🚀 เริ่มต้นแปลหนังสือทั้งหมด"):
    st.session_state.is_translating = True
    progress_bar = st.progress(0)
    status_text = st.empty()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp_in:
      tmp_in.write(uploaded_file.getbuffer())
      input_path = tmp_in.name

    output_path = input_path.replace(".epub", "_translated.epub")

    try:
      status_text.text("กำลังอ่านโครงสร้างไฟล์หนังสือ...")
      book = epub.read_epub(input_path)
      new_book = epub.EpubBook()

      try:
        book_id = book.identifier if book.identifier else "id123456"
      except Exception:
        book_id = "id123456"
      new_book.set_identifier(str(book_id))

      try:
        book_title = book.title if book.title else "Untitled Book"
      except Exception:
        book_title = "Untitled Book"

      is_bilingual = "แบบสองภาษา" in translation_mode
      new_book.set_title(
          book_title + (" (Bilingual)" if is_bilingual else " (Thai)")
      )
      new_book.set_language("th")

      try:
        authors = book.get_authors()
        if authors:
          for author in authors:
            new_book.add_author(author)
        else:
          new_book.add_author("Unknown Author")
      except Exception:
        new_book.add_author("Unknown Author")

      items = list(book.get_items())
      total_items = len(items)

      status_text.text(
          "กำลังแปลเนื้อหาหนังสือ (กระบวนการนี้อาจใช้เวลาตามความหนา"
          " ห้ามปิดหน้าเว็บจนกว่าจะเสร็จ)..."
      )

      for idx, item in enumerate(items):
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
          try:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            paragraphs = soup.find_all(["p", "h1", "h2", "h3", "h4"])
            for p in paragraphs:
              orig_text = p.get_text()
              if len(orig_text.strip()) > 2:
                translated = safe_translate(
                    orig_text, mode_bilingual=is_bilingual
                )
                p.string = translated
            item.set_content(str(soup).encode("utf-8"))
          except Exception:
            pass
        new_book.add_item(item)

        progress = min((idx + 1) / total_items, 1.0)
        progress_bar.progress(progress)

      epub.write_epub(output_path, new_book)
      st.session_state.translated_file_path = output_path
      st.session_state.is_translating = False
      status_text.text("✅ แปลหนังสือเสร็จสมบูรณ์เรียบร้อยแล้ว!")

    except Exception as e:
      st.session_state.is_translating = False
      st.error(f"เกิดข้อผิดพลาดขึ้นในกระบวนการ: {str(e)}")

  # แสดงปุ่มดาวน์โหลดหากมีไฟล์ที่แปลเสร็จแล้วค้างอยู่ในระบบ (Session)
  if st.session_state.translated_file_path:
    st.success("🎉 มีไฟล์แปลพร้อมดาวน์โหลดแล้ว!")
    with open(st.session_state.translated_file_path, "rb") as f:
      st.download_button(
          label="📥 ดาวน์โหลดไฟล์ EPUB ที่แปลแล้ว",
          data=f,
          file_name=uploaded_file.name.replace(".epub", "_Thai.epub"),
          mime="application/epub+zip",
      )
